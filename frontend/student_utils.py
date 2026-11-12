"""Các hàm xử lý dữ liệu sinh viên."""


def add_student(students: list[dict], student_id: str, name: str, score: float) -> bool:
    """Thêm một sinh viên và trả về True; trả về False nếu mã đã tồn tại."""
    student_id = student_id.strip()
    name = name.strip()

    if any(student["id"].lower() == student_id.lower() for student in students):
        return False

    students.append({"id": student_id, "name": name, "score": score})
    return True


def display_students(students: list[dict]) -> None:
    """Hiển thị danh sách sinh viên theo dạng bảng."""
    if not students:
        print("Danh sách sinh viên đang trống.")
        return

    print("\n{:<5} {:<15} {:<30} {:>10}".format("STT", "Mã SV", "Họ và tên", "Điểm"))
    print("-" * 65)
    for index, student in enumerate(students, start=1):
        print(
            "{:<5} {:<15} {:<30} {:>10.2f}".format(
                index, student["id"], student["name"], student["score"]
            )
        )


def calculate_average(students: list[dict]) -> float | None:
    """Trả về điểm trung bình của lớp, hoặc None nếu danh sách trống."""
    if not students:
        return None
    total = sum(student["score"] for student in students)
    return total / len(students)


def find_highest(students: list[dict]) -> list[dict]:
    """Trả về danh sách sinh viên có điểm cao nhất."""
    if not students:
        return []
    highest_score = max(student["score"] for student in students)
    return [student for student in students if student["score"] == highest_score]


def find_lowest(students: list[dict]) -> list[dict]:
    """Trả về danh sách sinh viên có điểm thấp nhất."""
    if not students:
        return []
    lowest_score = min(student["score"] for student in students)
    return [student for student in students if student["score"] == lowest_score]


def search_student(students: list[dict], keyword: str) -> list[dict]:
    """Tìm sinh viên theo mã hoặc một phần họ tên, không phân biệt hoa thường."""
    keyword = keyword.strip().lower()
    if not keyword:
        return []

    return [
        student
        for student in students
        if keyword in student["id"].lower() or keyword in student["name"].lower()
    ]
