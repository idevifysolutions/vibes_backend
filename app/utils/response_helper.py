def success_response(data, message: str, status_code: int = 200):
    return {
        "success": True,
        "status_code": status_code,
        "message": message,
        "data": data,
    }
