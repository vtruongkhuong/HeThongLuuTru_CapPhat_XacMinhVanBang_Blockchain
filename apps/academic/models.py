"""
Danh mục dùng chung: Khoa (Faculty), Ngành (Major), Loại văn bằng (DegreeType).

Đây là dữ liệu "tĩnh" - ít thay đổi, được các app khác (students, degrees)
tham chiếu tới qua ForeignKey.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Faculty(TimeStampedModel):
    """Khoa/Viện, ví dụ: Công nghệ thông tin, Kinh tế..."""

    code = models.CharField(max_length=20, unique=True, help_text="Vd: CNTT, KT")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'academic_faculty'
        ordering = ['name']
        verbose_name_plural = 'Faculties'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Major(TimeStampedModel):
    """Ngành đào tạo, thuộc 1 Khoa."""

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name='majors')
    code = models.CharField(max_length=20, unique=True, help_text="Vd: 7480201")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'academic_major'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class DegreeType(TimeStampedModel):
    """
    Loại văn bằng/chứng chỉ, ví dụ: Cử nhân, Kỹ sư, Thạc sĩ, Chứng chỉ...
    Dùng để chọn template PDF phù hợp khi generate degree.
    """

    code = models.CharField(max_length=20, unique=True, help_text="Vd: CN, KS, THS")
    name = models.CharField(max_length=255)
    level = models.CharField(max_length=50, null=True, blank=True, help_text="Vd: Đại học, Sau đại học")
    template_name = models.CharField(
        max_length=255, blank=True,
        help_text="Tên file template HTML dùng để render PDF (trong templates/degrees/pdf/)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'academic_degree_type'
        ordering = ['name']

    def __str__(self):
        return self.name