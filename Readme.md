# Document Q&A Application

This project is a Document Question & Answer (Q&A) web application that allows users to upload documents (such as PDFs), store them in a database, and ask questions about the content. The backend is built with Python, and the application uses a database to store document and Q&A data.

## Features
- **Document Upload:** Upload PDF or other document files via a web interface.
- **Database Storage:** Store documents and related metadata in a database (document_qa.db).
- **Question Answering:** Ask questions about uploaded documents and receive answers.
- **REST API:** Backend exposes endpoints for document upload, question answering, and data retrieval.
- **Docker Support:** Easily run the application using Docker and Docker Compose.

## Setup Instructions

### 1. Clone the Repository
```sh
git clone <repo-url>
cd Documents_Q-A
```

### 2. Install Dependencies
```sh
pip install -r requirements.txt
```

### 3. Run the Application
#### Using Python
```sh
python main.py
```

#### Using Docker
```sh
docker build -t document-qa .
docker-compose up
```

### 4. Access the Application
- Open your browser and go to `http://localhost:8000` (or the port specified in your configuration).
- Use upload_test.html to test document uploads.

## API Endpoints (Example)
- `POST /upload` — Upload a document
- `POST /ask` — Ask a question about a document
- `GET /documents` — List uploaded documents
- `GET /questions` — List questions and answers

## Database
- Uses SQLite (document_qa.db) by default.
- Models and database logic are defined in models.py and database.py.

## File Descriptions
- **main.py:** Starts the web server and includes the main application logic.
- **app/routers.py:** Defines API routes for document upload, Q&A, etc.
- **app/services.py:** Contains business logic for processing documents and answering questions.
- **app/schemas.py:** Pydantic models for request/response validation.
- **app/models.py:** ORM models for database tables.
- **app/database.py:** Database connection and session management.
- **app/enums.py:** Enum classes for status, types, etc.


## Deployment
- Use Docker and Docker Compose for easy deployment.
- Update environment variables and configuration as needed for production.

## Requirements
- Python 3.8+
- pip
- Docker (optional)

## License
This project is licensed under the MIT License.

## Author
- Shikhardeep Meena
