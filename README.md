# Sustainamart Trade-In System

supabase 

reward_orchestrator_boilerplate.txt (not complete but should be ok)

------------------------------------------

Service: `trade-in` --> Accepts product info + image upload

Port: `5400`

-------------------------------------------

Service: `verification` --> In house dashboard for approve/reject requests

Port: `5401`

-------------------------------------------

# Setup `.env` Files

Copy the `.env.example` files into actual `.env` files:

# bash

cp trade_in/.env.example trade_in/.env

cp verification/.env.example verification/.env

--------------------------------------------

# dir 

sustainamart/
├── docker-compose.yml
├── README.md
├── trade_in/
│   ├── app.py
│   ├── utils.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── verification/
│   ├── app.py
│   ├── utils.py
│   ├── templates/
│   │   └── index.html
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
