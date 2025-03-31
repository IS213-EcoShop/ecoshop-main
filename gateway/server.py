from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette_graphene3 import GraphQLApp, make_graphiql_handler
import graphene
from resolvers import fetch_cart, fetch_recommendations  # Import resolvers
from graphql_types import CartItemType, ProductType  # Removed CategoryEnum

class Query(graphene.ObjectType):
    cart = graphene.List(CartItemType, user_id=graphene.Int())
    recommendations = graphene.List(ProductType, user_id=graphene.Int())

    def resolve_cart(self, info, user_id):
        return fetch_cart(user_id)

    def resolve_recommendations(self, info, user_id):
        return fetch_recommendations(user_id)

# Define the GraphQL schema
schema = graphene.Schema(query=Query)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your Vue.js app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up GraphQL route with a GraphiQL interface
app.add_route("/graphql", GraphQLApp(schema=schema, on_get=make_graphiql_handler()))
