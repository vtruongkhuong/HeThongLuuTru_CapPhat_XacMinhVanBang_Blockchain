from rest_framework import serializers


class DegreeVerifyResponseSerializer(serializers.Serializer):
    """Serializer chuẩn cho kết quả xác minh văn bằng."""
    status = serializers.CharField()           # VERIFIED / TAMPERED / REVOKED / NOT_FOUND
    student_name = serializers.CharField()
    student_code = serializers.CharField()
    degree_type = serializers.CharField()
    major = serializers.CharField()
    issue_date = serializers.DateField(allow_null=True)
    degree_number = serializers.CharField()
    tx_hash = serializers.CharField(allow_null=True)
    block_number = serializers.IntegerField(allow_null=True)
    merkle_root = serializers.CharField(allow_null=True)
    etherscan_url = serializers.URLField(allow_null=True)
    verified_at = serializers.DateTimeField()
    is_revoked = serializers.BooleanField()


class HashVerifyRequestSerializer(serializers.Serializer):
    hash = serializers.CharField(
        max_length=64,
        help_text="Canonical hash (SHA-256, 64 ký tự hex) của văn bằng"
    )


class BatchVerifyRequestSerializer(serializers.Serializer):
    uuids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50,
        help_text="Danh sách UUID văn bằng cần kiểm tra (tối đa 50)"
    )