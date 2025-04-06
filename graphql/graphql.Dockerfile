FROM python:3-slim

WORKDIR /usr/src/app

# Copy the requirements file first, install dependencies
COPY ./graphql/requirements.txt ./
COPY ./utils ./utils
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./graphql/server.py ./
COPY ./graphql/resolvers.py ./
COPY ./graphql/graphql_types.py ./

# Expose the application port 
EXPOSE 5205

# Set the command to run the application using Uvicorn (FastAPI) on port 5205
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5205"]
