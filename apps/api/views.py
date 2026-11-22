import logging
from uuid import UUID
from django.utils import timezone
from django.apps import apps

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.degrees.models import Degree
from apps.verification.views import _verify_merkle_and_contract
from .serializers import (
    DegreeVerifyResponseSerializer,
    HashVerifyRequestSerializer,
    BatchVerifyRequestSerializer,
)
from .authentication import APIKeyAuthentication
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def _build_verify_result(degree):
    """Hàm nội bộ: xác minh 1 văn bằng và trả về dict kết quả chuẩn."""
    is_valid, is_revoked, proof_info, rpc_error = _verify_merkle_and_contract(degree)

    issuance_batch = None
    try:
        DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
        proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
        issuance_batch = getattr(proof_obj, 'issuance_batch', None)
    except Exception:
        pass
    if not issuance_batch and degree.batch:
        issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

    tx_hash = getattr(degree, 'tx_hash', None) or getattr(issuance_batch, 'tx_hash', None)
    merkle_root = (
        proof_info.get('chain_merkle_root')
        or proof_info.get('local_merkle_root')
        or getattr(issuance_batch, 'merkle_root', None)
    )

    if is_revoked or degree.status == 'REVOKED':
        result_status = 'REVOKED'
    elif degree.status == 'ISSUED':
        result_status = 'VERIFIED'
    else:
        result_status = 'NOT_FOUND'

    return {
        'status': result_status,
        'student_name': degree.student.full_name if degree.student else '',
        'student_code': degree.student.student_code if degree.student else '',
        'degree_type': degree.degree_type.name if degree.degree_type else '',
        'major': degree.student.major.name if (degree.student and degree.student.major) else '',
        'issue_date': degree.issue_date,
        'degree_number': degree.serial_number,
        'tx_hash': tx_hash,
        'block_number': None,
        'merkle_root': merkle_root,
        'etherscan_url': f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None,
        'verified_at': timezone.now(),
        'is_revoked': (is_revoked or degree.status == 'REVOKED'),
    }


class VerifyByUUIDView(APIView):
    """GET /api/v1/verify/<uuid>/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Xác minh văn bằng theo UUID",
        description="Trả về trạng thái hợp lệ, thông tin sinh viên và bằng chứng Blockchain.",
        parameters=[OpenApiParameter('uuid', str, description='UUID văn bằng (credential_public_id)')],
        responses={
            200: DegreeVerifyResponseSerializer,
            404: OpenApiResponse(description='Không tìm thấy văn bằng'),
        },
    )
    def get(self, request, uuid):
        try:
            degree = Degree.objects.select_related(
                'student', 'student__major', 'degree_type', 'batch'
            ).get(credential_public_id=UUID(str(uuid)))
        except (Degree.DoesNotExist, ValueError):
            return Response({'detail': 'Không tìm thấy văn bằng.'}, status=status.HTTP_404_NOT_FOUND)

        result = _build_verify_result(degree)
        return Response(DegreeVerifyResponseSerializer(result).data)


class VerifyByHashView(APIView):
    """POST /api/v1/verify/hash/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Xác minh văn bằng theo canonical hash",
        description='Body JSON: {"hash": "<64 ký tự hex SHA-256>"}',
        request=HashVerifyRequestSerializer,
        responses={
            200: DegreeVerifyResponseSerializer,
            400: OpenApiResponse(description='Thiếu hoặc sai định dạng hash'),
            404: OpenApiResponse(description='Không tìm thấy văn bằng'),
        },
    )
    def post(self, request):
        ser = HashVerifyRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        hash_val = ser.validated_data['hash'].replace('0x', '').lower()
        try:
            degree = Degree.objects.select_related(
                'student', 'student__major', 'degree_type', 'batch'
            ).get(canonical_hash__iexact=hash_val)
        except Degree.DoesNotExist:
            return Response({'detail': 'Không tìm thấy văn bằng với hash này.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(DegreeVerifyResponseSerializer(_build_verify_result(degree)).data)


class VerifyBatchView(APIView):
    """POST /api/v1/verify/batch/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Xác minh hàng loạt văn bằng",
        description='Body JSON: {"uuids": ["<uuid1>", "<uuid2>", ...]} — tối đa 50 UUID',
        request=BatchVerifyRequestSerializer,
        responses={
            200: OpenApiResponse(description='results[] + summary{total/verified/tampered/revoked/not_found}'),
            400: OpenApiResponse(description='Dữ liệu đầu vào không hợp lệ'),
        },
    )
    def post(self, request):
        ser = BatchVerifyRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        uuids = ser.validated_data['uuids']
        summary = {'total': len(uuids), 'verified': 0, 'revoked': 0, 'tampered': 0, 'not_found': 0}

        degrees_map = {
            str(d.credential_public_id): d
            for d in Degree.objects.select_related(
                'student', 'student__major', 'degree_type', 'batch'
            ).filter(credential_public_id__in=uuids)
        }

        results = []
        for uuid_val in uuids:
            degree = degrees_map.get(str(uuid_val))
            if not degree:
                result = {
                    'status': 'NOT_FOUND', 'student_name': '', 'student_code': '',
                    'degree_type': '', 'major': '', 'issue_date': None,
                    'degree_number': '', 'tx_hash': None, 'block_number': None,
                    'merkle_root': None, 'etherscan_url': None,
                    'verified_at': timezone.now(), 'is_revoked': False,
                }
                summary['not_found'] += 1
            else:
                result = _build_verify_result(degree)
                s = result['status']
                if s == 'VERIFIED': summary['verified'] += 1
                elif s == 'REVOKED': summary['revoked'] += 1
                elif s == 'TAMPERED': summary['tampered'] += 1
                else: summary['not_found'] += 1
            results.append(result)

        return Response({
            'results': DegreeVerifyResponseSerializer(results, many=True).data,
            'summary': summary,
        })