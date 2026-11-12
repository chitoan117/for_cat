"""Chương trình quản lý sinh viên chạy trên terminal."""

from file_utils import load_csv, save_csv
from student_utils import (
    add_student,
    calculate_average,
    display_students,
    find_highest,
    find_lowest,
    search_student,
)


def show_menu() -> None:
    print(
        """
========== QUẢN LÝ SINH VIÊN ==========
1. Thêm sinh viên
2. Hiển thị danh sách
3. Tính điểm trung bình
4. Tìm sinh viên điểm cao nhất
5. Tìm sinh viên điểm thấp nhất
6. Tìm kiếm sinh viên
7. Lưu danh sách vào CSV
8. Đọc danh sách từ CSV
0. Thoát
========================================
"""
    )


def input_score() -> float:
    """Nhập và kiểm tra điểm trong khoảng từ 0 đến 10."""
    while True:
        try:
            score = float(input("Nhập điểm (0-10): "))
            if 0 <= score <= 10:
                return score
            print("Điểm phải nằm trong khoảng từ 0 đến 10.")
        except ValueError:
            print("Điểm phải là một số. Vui lòng nhập lại.")


def handle_add(students: list[dict]) -> None:
    student_id = input("Nhập mã sinh viên: ").strip()
    name = input("Nhập họ và tên: ").strip()

    if not student_id or not name:
        print("Mã sinh viên và họ tên không được để trống.")
        return

    score = input_score()
    if add_student(students, student_id, name, score):
        print("Đã thêm sinh viên thành công.")
    else:
        print("Mã sinh viên đã tồn tại.")


def handle_average(students: list[dict]) -> None:
    average = calculate_average(students)
    if average is None:
        print("Danh sách sinh viên đang trống.")
    else:
        print(f"Điểm trung bình của lớp: {average:.2f}")


def handle_search(students: list[dict]) -> None:
    keyword = input("Nhập mã hoặc tên cần tìm: ")
    results = search_student(students, keyword)
    if results:
        display_students(results)
    else:
        print("Không tìm thấy sinh viên phù hợp.")


def handle_save(students: list[dict]) -> None:
    file_name = input("Tên file CSV [students.csv]: ").strip() or "students.csv"
    if save_csv(students, file_name):
        print(f"Đã lưu {len(students)} sinh viên vào '{file_name}'.")


def handle_load() -> list[dict] | None:
    file_name = input("Tên file CSV [students.csv]: ").strip() or "students.csv"
    loaded_students = load_csv(file_name)
    if loaded_students is not None:
        print(f"Đã đọc {len(loaded_students)} sinh viên từ '{file_name}'.")
    return loaded_students


def main() -> None:
    students: list[dict] = []

    while True:
        show_menu()
        choice = input("Chọn chức năng: ").strip()

        if choice == "1":
            handle_add(students)
        elif choice == "2":
            display_students(students)
        elif choice == "3":
            handle_average(students)
        elif choice == "4":
            highest_students = find_highest(students)
            print("Sinh viên có điểm cao nhất:")
            display_students(highest_students)
        elif choice == "5":
            lowest_students = find_lowest(students)
            print("Sinh viên có điểm thấp nhất:")
            display_students(lowest_students)
        elif choice == "6":
            handle_search(students)
        elif choice == "7":
            handle_save(students)
        elif choice == "8":
            loaded_students = handle_load()
            if loaded_students is not None:
                students = loaded_students
        elif choice == "0":
            print("Đã thoát chương trình. Hẹn gặp lại!")
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng chọn từ 0 đến 8.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nĐã thoát chương trình.")
