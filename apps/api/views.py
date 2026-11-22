import json as json_lib
import logging
from uuid import UUID
from django.http import HttpResponse
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
    BatchVerifyResponseSerializer,
    IPFSUploadResponseSerializer,
)
from .authentication import APIKeyAuthentication
from .vc_generator import generate_verifiable_credential
from apps.blockchain.ipfs import pin_file_to_ipfs
from rest_framework.permissions import IsAuthenticated, AllowAny

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
            200: BatchVerifyResponseSerializer,
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


class DownloadVerifiableCredentialView(APIView):
    """GET /api/v1/degrees/<uuid>/credential.json — Task 7: W3C Verifiable Credential"""
    authentication_classes = []  # Công khai: sinh viên trên web hoặc NTD đều tải được
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Tải W3C Verifiable Credential JSON",
        description="Trả về file JSON chuẩn W3C VC Data Model v1.1 cho văn bằng, dùng để xác minh độc lập.",
        parameters=[OpenApiParameter('uuid', str, description='credential_public_id của văn bằng')],
        request=None,
        responses={
            200: OpenApiResponse(description='JSON file — W3C Verifiable Credential'),
            400: OpenApiResponse(description='Văn bằng chưa phát hành on-chain'),
            404: OpenApiResponse(description='Không tìm thấy văn bằng'),
        },
    )
    def get(self, request, uuid):
        try:
            degree = Degree.objects.select_related(
                'student', 'student__major', 'student__faculty',
                'degree_type', 'batch',
            ).get(credential_public_id=UUID(str(uuid)))
        except (Degree.DoesNotExist, ValueError):
            return Response({'detail': 'Không tìm thấy văn bằng.'}, status=status.HTTP_404_NOT_FOUND)

        if degree.status != 'ISSUED':
            return Response(
                {'detail': 'Chỉ văn bằng đã phát hành on-chain (ISSUED) mới có Verifiable Credential.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            vc = generate_verifiable_credential(degree)
        except Exception as e:
            logger.error(f"[VC] Lỗi tạo VC cho degree {uuid}: {e}", exc_info=True)
            return Response({'detail': 'Lỗi khi tạo Verifiable Credential.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        file_name = f"credential-{degree.serial_number}.json"
        response = HttpResponse(
            json_lib.dumps(vc, ensure_ascii=False, indent=2),
            content_type='application/json',
        )
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response


class IPFSUploadView(APIView):
    """POST /api/v1/degrees/<uuid>/ipfs-upload/ — Task 8: IPFS Upload"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Upload PDF văn bằng lên IPFS",
        description=(
            "Tải file PDF của văn bằng lên IPFS (Pinata nếu có key, fallback tính CID offline). "
            "Cập nhật ipfs_cid và ipfs_url vào DB."
        ),
        parameters=[OpenApiParameter('uuid', str, description='credential_public_id của văn bằng')],
        request=None,
        responses={
            200: IPFSUploadResponseSerializer,
            404: OpenApiResponse(description='Không tìm thấy văn bằng'),
            400: OpenApiResponse(description='File PDF không tồn tại hoặc lỗi upload'),
        },
    )
    def post(self, request, uuid):
        try:
            degree = Degree.objects.select_related('student', 'degree_type').get(
                credential_public_id=UUID(str(uuid))
            )
        except (Degree.DoesNotExist, ValueError):
            return Response({'detail': 'Không tìm thấy văn bằng.'}, status=status.HTTP_404_NOT_FOUND)

        import os
        from django.conf import settings as django_settings

        # Nếu đã có CID rồi thì trả về luôn
        if degree.ipfs_cid:
            return Response({
                'cid': degree.ipfs_cid,
                'ipfs_url': degree.ipfs_url,
                'student_name': degree.student.full_name if degree.student else '',
                'degree_number': degree.serial_number,
                'already_uploaded': True,
            })

        # Tìm PDF
        pdf_path = None
        if degree.pdf_path:
            candidate = degree.pdf_path
            if not os.path.isabs(candidate):
                candidate = os.path.join(django_settings.MEDIA_ROOT, candidate)
            if os.path.exists(candidate):
                pdf_path = candidate

        if not pdf_path:
            # Fallback: tính CID từ canonical_hash bytes (đại diện cho nội dung văn bằng)
            content = degree.canonical_hash.encode('utf-8') if degree.canonical_hash else b''
        else:
            with open(pdf_path, 'rb') as f:
                content = f.read()

        try:
            file_name = f"degree-{degree.serial_number}.pdf"
            metadata = {
                'student_code': degree.student.student_code if degree.student else '',
                'serial_number': degree.serial_number,
                'canonical_hash': degree.canonical_hash or '',
            }
            cid, ipfs_url = pin_file_to_ipfs(content, file_name=file_name, metadata=metadata)
        except Exception as e:
            logger.error(f"[IPFS] Lỗi upload degree {uuid}: {e}", exc_info=True)
            return Response({'detail': f'Lỗi khi upload IPFS: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Lưu vào DB
        degree.ipfs_cid = cid
        degree.ipfs_url = ipfs_url
        degree.save(update_fields=['ipfs_cid', 'ipfs_url'])

        return Response({
            'cid': cid,
            'ipfs_url': ipfs_url,
            'student_name': degree.student.full_name if degree.student else '',
            'degree_number': degree.serial_number,
            'already_uploaded': False,
        })