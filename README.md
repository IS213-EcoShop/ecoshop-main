# SustainaMart

SustainaMart is a scalable, microservices-based eCommerce platform promoting sustainable living through eco-friendly products and gamified engagement. Built using Flask, Kong API Gateway, RabbitMQ, and Swagger, the platform is designed for modularity, scalability, and a seamless developer experience.

---

## Features

- Eco-focused eCommerce with product recommendations and carbon-conscious delivery options
- Microservices architecture for modularity and scalability
- RabbitMQ for asynchronous, event-driven communication
- Swagger/OpenAPI documentation for all services
- Kong API Gateway for unified routing and service discovery
- Gamification layer with missions, rewards, leaderboard, and vouchers

---

## Requirements

- Backend: Python (Flask)
- API Gateway: Kong (DB-less mode)
- Messaging: RabbitMQ
- Documentation: Swagger / OpenAPI 3
- Containerization: Docker + Docker Compose

---

### Frontend Setup
1. Clone the frontend repository:

```bash
git clone https://github.com/IS213-EcoShop/ecoshop-frontend.git
cd ecoshop-frontend/sustainamart
```
2. Install dependencies:
```bash
npm install
npm install vite
npm install @supabase/supabase-js
```
3. Run the frontend (from inside sustainamart/ directory of the frontend):
```bash
npm run dev
```
4. Frontend will be accessible at:
```bash
http://localhost:5173
```

### Backend Setup
1. Build and start the backend microservices:
```bash
docker compose build --no-cache && docker compose up

```

2. Additional:
- Verification UI can be accessed at:
```bash
  http://localhost:5401/
```



## Microservices Overview

| Service | Description |
|---------|-------------|
| `profile` | User authentication and profile management |
| `cart` | Shopping cart logic |
| `cart-product` | Handles cart-product linkage |
| `payment` | Payment handling and processing |
| `place_order` | Coordinates order creation |
| `recommendation` | Personalized product recommendations |
| `graphql` | Aggregated GraphQL layer |
| `wallet` | Virtual wallet service |
| `mission` | Daily/weekly user engagement tasks |
| `leaderboard` | Leaderboard rankings by points |
| `reward_orchestrator` | Central controller for rewards logic |
| `voucher` | Voucher generation and redemption |
| `trade_in` | Used item trade-in feature |
| `verification` | External services verification |
| `intermediary` | Middleware for coordination logic |
| `delivery` | Delivery scheduling and management |

---

## Tech Stack

- Backend: Python (Flask)
- API Gateway: Kong (DB-less mode)
- Messaging: RabbitMQ
- Documentation: Swagger / OpenAPI 3
- Containerization: Docker + Docker Compose

---

## Documentation

You can view the full integrated API documentation here:
🔗 [SustainaMart API Documentation on SwaggerHub](https://app.swaggerhub.com/apis/IMRANSHAHMIBINSENAN_/sustaina-mart_api_documentation/1.0.0)





