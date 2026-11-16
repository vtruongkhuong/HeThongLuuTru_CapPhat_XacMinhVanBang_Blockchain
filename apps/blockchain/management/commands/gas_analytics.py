from django.core.management.base import BaseCommand
from demo_gas_analytics import print_gas_report

class Command(BaseCommand):
    help = "Xuất báo cáo phân tích và đo lường chi phí Gas On-Chain (Ethereum Sepolia)"

    def handle(self, *args, **options):
        print_gas_report()
