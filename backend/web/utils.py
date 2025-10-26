from datetime import timedelta

def get_width_height(aspect_ratio):
    if aspect_ratio == "16:9":
        return 1024, 576
    elif aspect_ratio == "9:16":
        return 576, 1024
    elif aspect_ratio == "1:1":
        return 768, 768
    elif aspect_ratio == "4:3":
        return 960, 720
    elif aspect_ratio == "3:4":
        return 720, 960
    else:
        return 1024, 576  # default 

def utc_to_wib(dt):
    if dt is None:
        return None
    return dt + timedelta(hours=7) 

def format_tanggal_indonesia(dt):
    if dt is None:
        return ""
    bulan_id = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{dt.day:02d} {bulan_id[dt.month-1]} {dt.year} {dt.strftime('%H:%M')}" 