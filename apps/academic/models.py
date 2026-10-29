"""
Danh mục dùng chung: Khoa (Faculty), Ngành (Major), Loại văn bằng (DegreeType).

Đây là dữ liệu "tĩnh" - ít thay đổi, được các app khác (students, degrees)
tham chiếu tới qua ForeignKey.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Faculty(TimeStampedModel):
    """Khoa/Viện, ví dụ: Công nghệ thông tin, Kinh tế..."""

    code = models.CharField(max_length=20, unique=True, verbose_name="Mã khoa")
    name = models.CharField(max_length=255, verbose_name="Tên khoa")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")

    class Meta:
        db_table = 'academic_faculty'
        ordering = ['name']
        verbose_name = "Khoa đào tạo"
        verbose_name_plural = 'Danh mục Khoa đào tạo'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Major(TimeStampedModel):
    """Ngành đào tạo, thuộc 1 Khoa."""

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name='majors', verbose_name="Khoa trực thuộc")
    
    degree_type = models.ForeignKey(
        'DegreeType', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        help_text="Loại văn bằng sẽ cấp cho ngành này",
        verbose_name="Loại văn bằng chuẩn"
    )
    
    code = models.CharField(max_length=20, unique=True, help_text="Vd: 7480201", verbose_name="Mã ngành")
    name = models.CharField(max_length=255, verbose_name="Tên ngành")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")

    class Meta:
        db_table = 'academic_major'
        ordering = ['name']
        verbose_name = "Ngành đào tạo"
        verbose_name_plural = "Danh mục Ngành đào tạo"

    def __str__(self):
        return f"{self.code} - {self.name}"


class DegreeType(TimeStampedModel):
    """
    Loại văn bằng/chứng chỉ, ví dụ: Cử nhân, Kỹ sư, Thạc sĩ, Chứng chỉ...
    Dùng để chọn template PDF phù hợp khi generate degree.
    """

    code = models.CharField(max_length=20, unique=True, verbose_name="Mã loại bằng", help_text="Vd: CN, KS, THS")
    name = models.CharField(max_length=255, verbose_name="Tên loại bằng")
    level = models.CharField(max_length=50, null=True, blank=True, verbose_name="Bậc đào tạo", help_text="Vd: Đại học, Sau đại học")
    template_name = models.CharField(
        max_length=255, blank=True,verbose_name="Mẫu phôi PDF",
        help_text="Tên file template HTML dùng để render PDF (trong templates/degrees/pdf/)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")

    class Meta:
        db_table = 'academic_degree_type'
        ordering = ['name']
        verbose_name = "Loại văn bằng"
        verbose_name_plural = "Danh mục Loại văn bằng"

    def __str__(self):
        return self.name