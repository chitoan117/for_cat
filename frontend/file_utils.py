"""Các hàm đọc và ghi danh sách sinh viên bằng file CSV."""

import csv


FIELD_NAMES = ["id", "name", "score"]


def save_csv(students: list[dict], file_name: str) -> bool:
    """Ghi danh sách sinh viên vào CSV và trả về trạng thái thành công."""
    try:
        with open(file_name, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
            writer.writeheader()
            writer.writerows(students)
        return True
    except (OSError, csv.Error) as error:
        print(f"Không thể lưu file: {error}")
        return False


def load_csv(file_name: str) -> list[dict] | None:
    """Đọc CSV và trả về danh sách sinh viên; trả về None nếu có lỗi."""
    students = []
    try:
        with open(file_name, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None or not set(FIELD_NAMES).issubset(reader.fieldnames):
                raise ValueError("File CSV phải có các cột: id, name, score")

            for line_number, row in enumerate(reader, start=2):
                student_id = (row.get("id") or "").strip()
                name = (row.get("name") or "").strip()
                score = float(row.get("score", ""))

                if not student_id or not name:
                    raise ValueError(f"Dữ liệu trống ở dòng {line_number}")
                if not 0 <= score <= 10:
                    raise ValueError(f"Điểm không hợp lệ ở dòng {line_number}")
                if any(student["id"].lower() == student_id.lower() for student in students):
                    raise ValueError(f"Mã sinh viên bị trùng ở dòng {line_number}")

                students.append({"id": student_id, "name": name, "score": score})

        return students
    except FileNotFoundError:
        print(f"Không tìm thấy file '{file_name}'.")
    except (OSError, csv.Error, ValueError) as error:
        print(f"Không thể đọc file: {error}")
    return None
