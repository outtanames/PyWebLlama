## Getting Started

### Demo
Demo youtube [link](https://youtu.be/z8I_zJ5VmyE)

### Prerequisites

- Node.js (v20 or later)
- Python (v3.11 or later)
- Docker and Docker Compose (optional, for containerized deployment)

### Clean

```sh
rm -rf *.png
```

### Installation

1. Clone the repository:

   ```sh
   git clone <url>
   cd metamodel
   ```

2. Set up the frontend:

   ```sh
   cd frontend
   echo "VITE_API_URL=http://localhost:8000" > .env  # Set the API URL
   npm install
   ```

3. Set up the backend:

   ```sh
   cd ../backend
   echo "BACKEND_CORS_ORIGINS=http://localhost,http://localhost:5173" > .env  # Optional: set the CORS origins (separated by commas)
   pip install -r requirements.txt
   ```

### Running the Application

1. Start the backend server:

   ```sh
   cd backend
   uvicorn app.main:app --reload
   ```

2. In a new terminal, start the frontend development server:

   ```sh
   cd frontend
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173` to use.



## Docker Deployment

To deploy the application using Docker:

1. Ensure Docker and Docker Compose are installed on your system.
2. Edit `.env` file in the root directory and set your environment variables, for example:

   ```sh
   VITE_API_URL=http://localhost:8000
   BACKEND_CORS_ORIGINS="http://localhost,http://localhost:5173"
   ```

3. Run the following command in the root directory:

   ```sh
   docker compose up --build
   ```

4. Access the application at `http://localhost:80`.

It is also possible to deploy frontend and backend separately using their respective Dockerfile and environment variables.

