from django.db import models

class IssuanceBatch(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('FAILED', 'Failed'),
    ]

    graduation_batch = models.ForeignKey('graduation.GraduationBatch', on_delete=models.CASCADE, related_name='issuance_batches')
    merkle_root = models.CharField(max_length=66, null=True, blank=True)
    chain_id = models.CharField(max_length=50, null=True, blank=True)
    network_name = models.CharField(max_length=50, null=True, blank=True)
    contract_address = models.CharField(max_length=42, null=True, blank=True)
    contract_version = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

class DegreeMerkleProof(models.Model):
    degree = models.OneToOneField('degrees.Degree', on_delete=models.CASCADE, related_name='merkle_proof')
    issuance_batch = models.ForeignKey(IssuanceBatch, on_delete=models.CASCADE, related_name='proofs')
    leaf_hash = models.CharField(max_length=64)
    leaf_index = models.IntegerField()
    proof_path = models.JSONField()

class BlockchainTransaction(models.Model):
    OP_CHOICES = [
        ('ISSUE', 'Issue'),
        ('RETRY', 'Retry'),
        ('REVOKE', 'Revoke'),
        ('SYNC', 'Sync'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]

    issuance_batch = models.ForeignKey(IssuanceBatch, on_delete=models.CASCADE, null=True, blank=True)
    degree = models.ForeignKey('degrees.Degree', on_delete=models.CASCADE, null=True, blank=True)
    operation_type = models.CharField(max_length=20, choices=OP_CHOICES)
    tx_hash = models.CharField(max_length=66, unique=True)
    block_number = models.BigIntegerField(null=True, blank=True)
    gas_used = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)