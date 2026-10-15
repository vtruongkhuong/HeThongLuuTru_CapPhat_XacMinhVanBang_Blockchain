def get_classification_from_gpa(gpa):
    try:
        gpa = float(gpa)
    except (TypeError, ValueError):
        return "KHÔNG XẾP LOẠI"
    if gpa >= 3.6: return "XUẤT SẮC"
    if gpa >= 3.2: return "GIỎI"
    if gpa >= 2.5: return "KHÁ"
    if gpa >= 2.0: return "TRUNG BÌNH"
    return "KÉM"