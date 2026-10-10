import httpx
print("Testing CORS with good origin")
r = httpx.options("http://127.0.0.1:8000/api/labs/search?standard=IS%201786:2008", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "GET"
})
print("Good origin status:", r.status_code)
print("Good origin headers:", r.headers.get("access-control-allow-origin"))

print("Testing CORS with bad origin")
r = httpx.options("http://127.0.0.1:8000/api/labs/search?standard=IS%201786:2008", headers={
    "Origin": "http://evil.com",
    "Access-Control-Request-Method": "GET"
})
print("Bad origin headers:", r.headers.get("access-control-allow-origin"))
