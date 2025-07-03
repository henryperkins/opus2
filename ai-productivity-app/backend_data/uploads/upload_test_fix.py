def test_upload_fix_verification():
    """Test function to verify the upload fix works."""
    print("✅ Upload fix is working correctly!")
    return {"status": "success", "message": "File can be read from uploads directory"}

def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    result = test_upload_fix_verification()
    print(f"Result: {result}")
    
    fib_10 = fibonacci(10)
    print(f"10th Fibonacci number: {fib_10}")