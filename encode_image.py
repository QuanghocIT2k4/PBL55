import base64
import os
import sys

def image_to_base64_data_uri(image_path):
    """
    Chuyển đổi file ảnh thành chuỗi Data URI Base64.

    Args:
        image_path (str): Đường dẫn đầy đủ đến file ảnh.

    Returns:
        str: Chuỗi Data URI Base64 (ví dụ: "data:image/jpeg;base64,...")
             hoặc None nếu có lỗi.
    """
    try:
        # Kiểm tra file tồn tại
        if not os.path.isfile(image_path):
            print(f"Lỗi: Không tìm thấy file tại '{image_path}'")
            return None

        # Lấy phần mở rộng file (đuôi file) và chuyển thành chữ thường
        try:
            file_ext = os.path.basename(image_path).split('.')[-1].lower()
        except IndexError:
            print("Lỗi: Không thể xác định phần mở rộng của file.")
            return None

        # Xác định MIME type dựa trên phần mở rộng
        if file_ext in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif file_ext == 'png':
            mime_type = 'image/png'
        elif file_ext == 'gif':
            mime_type = 'image/gif'
        # Thêm các định dạng khác nếu cần (webp, bmp,...)
        # elif file_ext == 'webp':
        #     mime_type = 'image/webp'
        else:
            print(f"Lỗi: Định dạng file '.{file_ext}' không được hỗ trợ trong ví dụ này.")
            print("Các định dạng hỗ trợ: jpg, jpeg, png, gif.")
            return None

        # Đọc nội dung file ảnh ở chế độ nhị phân ('rb')
        with open(image_path, "rb") as img_file:
            # Đọc toàn bộ nội dung file
            img_binary_content = img_file.read()

            # Mã hóa nội dung nhị phân sang Base64 (kết quả là bytes)
            img_base64_bytes = base64.b64encode(img_binary_content)

            # Chuyển đổi bytes Base64 thành chuỗi UTF-8
            img_base64_string = img_base64_bytes.decode("utf-8")

            # Tạo chuỗi Data URI hoàn chỉnh
            data_uri = f"data:{mime_type};base64,{img_base64_string}"

            return data_uri

    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file ảnh tại '{image_path}'")
        return None
    except Exception as e:
        print(f"Lỗi không xác định xảy ra: {e}")
        return None

# --- Phần chạy chính của script ---
if __name__ == "__main__":
    # Hỏi người dùng nhập đường dẫn file ảnh
    print("---------------------------------------------")
    print("Tiện ích chuyển đổi ảnh sang Base64 Data URI")
    print("---------------------------------------------")
    image_file_path = input(">> Nhập đường dẫn đầy đủ đến file ảnh cần chuyển đổi: ")

    # Xử lý dấu ngoặc kép nếu người dùng kéo thả file vào terminal (trên Windows)
    image_file_path = image_file_path.strip().strip('"')

    # Gọi hàm chuyển đổi
    base64_data_uri = image_to_base64_data_uri(image_file_path)

    # In kết quả nếu thành công
    if base64_data_uri:
        print("\n--- CHUỖI DATA URI BASE64 (Sẵn sàng để copy) ---")
        print(base64_data_uri)
        print("-" * 49)
        print("Hướng dẫn: Copy toàn bộ chuỗi ở trên (bắt đầu từ 'data:image/...')")
        print("           và dán vào trường 'image_base64' trong JSON body của Postman.")
    else:
        print("\nChuyển đổi thất bại. Vui lòng kiểm tra lại đường dẫn và định dạng file.")

    print("\nNhấn Enter để thoát.")
    input() # Giữ cửa sổ terminal mở cho đến khi người dùng nhấn Enter