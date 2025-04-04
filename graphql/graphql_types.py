import graphene

# Define the ProductType
class ProductType(graphene.ObjectType):
    productId = graphene.Int()
    name = graphene.String()
    category = graphene.String()  
    condition = graphene.String()
    description = graphene.String()
    image_url = graphene.String()
    price = graphene.Float()
    sustainability_points = graphene.Int()
    tag_class = graphene.String()

# Define the CartItemType (inherits from ProductType)
class CartItemType(ProductType):
    quantity = graphene.Int()
