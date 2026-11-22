from django.db import migrations


def link_revocation_degrees(apps, schema_editor):
    BlockchainTransaction = apps.get_model('blockchain', 'BlockchainTransaction')
    RevocationRequest = apps.get_model('revocation', 'RevocationRequest')

    for rev in RevocationRequest.objects.exclude(tx_hash__isnull=True).exclude(tx_hash=''):
        tx = BlockchainTransaction.objects.filter(tx_hash=rev.tx_hash).first()
        if tx and not tx.degree:
            tx.degree = rev.degree
            tx.save(update_fields=['degree'])

    # Backfill khối và gas cho các giao dịch mock trước đó
    mock_data = {
        '0x73ee07e7d9c9807ff2cfe11e117c4759ec9356db6ce73f27c0903e8ee0922433': (11905240, 218450),
        '0xa3a6e88ca86275c5ae3616455ddba6d77f5e27c40264ce4e92df5a5fd9e95f7b': (11918730, 224600),
    }
    for h, (blk, gas) in mock_data.items():
        t = BlockchainTransaction.objects.filter(tx_hash=h, block_number__isnull=True).first()
        if t:
            t.block_number = blk
            t.gas_used = gas
            t.save(update_fields=['block_number', 'gas_used'])


def reverse_link(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blockchain', '0004_alter_issuancebatch_chain_id'),
        ('revocation', '0002_revocationrequest_supersedes_and_more'),
    ]

    operations = [
        migrations.RunPython(link_revocation_degrees, reverse_code=reverse_link),
    ]
