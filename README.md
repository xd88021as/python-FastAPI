# Identity Verification

使用 FastAPI 建立的實名認證 API 服務

## 運行方式

- uvicorn
    ```
    python -m pip install --upgrade pip 
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
- [gunicorn](https://stackoverflow.com/a/68579951/5269826)
    ```
    python -m pip install --upgrade pip 
    pip install -r requirements.txt
    sudo apt install gunicorn
    python -m gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    ```

## API 文件
- 運行後進入 http://localhost:8000/docs 可瀏覽交互式 API 文件 (OpenAPI)

