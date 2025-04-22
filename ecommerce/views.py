# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
from django.db.models import Avg 
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
import random
from django.db.models import Sum, F
from django.http import JsonResponse


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome aboard.")
            return redirect('home')  # homepage 
        else:
            messages.error(request, "Registration failed. Please try again.")
    else:
        form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})


def custom_login(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email_or_username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email_or_username, password=password)
            if user:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('home')  # Redirect to dashboard
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomAuthenticationForm()
    return render(request, "login.html", {"form": form})


def custom_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')  # Redirect to login page after logout



def home_view(request):

    sponsored_products = Product.objects.filter(is_sponsored=True)[:10]  # Example, modify as needed

    product_categories = Category.objects.all()
    top_sold_products = Product.objects.order_by('-stock')[:10]  # Example: Replace 'stock' with actual sales tracking field
    top_selling_products = Product.objects.order_by('-sales_count')[:6]  

    # Fetch a random set of products (e.g., 6 products for Daily Finds)
    all_products = list(Product.objects.all())  # Convert QuerySet to list
    daily_finds = random.sample(all_products, min(len(all_products), 15))  # Get up to 6 random products

    #new views 
    # Get all categories that have at least one product
    categories_with_products = []
    
    for category in Category.objects.all():
        products = list(category.products.all())
        if products:  # Only add categories that have products
            categories_with_products.append({
                'category': category,
                'products': products
            })
    
    # If we have fewer than 4 categories with products, use all of them
    # Otherwise, randomly select 4
    if len(categories_with_products) <= 4:
        selected_category_data = categories_with_products
    else:
        selected_category_data = random.sample(categories_with_products, 4)
    
    # Create the final data structure with one random product per category
    category_product_pairs = []
    for item in selected_category_data:
        category = item['category']
        random_product = random.choice(item['products'])
        category_product_pairs.append({
            'category': category,
            'product': random_product
        })


    context = {
       
        'sponsored_products': sponsored_products,
        'product_categories': product_categories,
        'top_sold_products': top_sold_products,
        'top_selling_products': top_selling_products,
        'daily_finds': daily_finds,
        'category_product_pairs': category_product_pairs
    }
    return render(request, 'home.html', context)

def product_list_view(request):
    products = Product.objects.all()
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'e-commerce/product_list.html', {'page_obj': page_obj})


def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    seller = product.seller  # Assuming Product has a ForeignKey to Seller

    #recently views using sessions 
    # Initialize the recently viewed products list in session if not present
    recently_viewed = request.session.get('recently_viewed', [])

    # Add the current product's slug if it's not already in the list
    if product.slug not in recently_viewed:
        recently_viewed.append(product.slug)

    # Limit the list to, for example, 5 products
    if len(recently_viewed) > 6:
        recently_viewed.pop(0)

    # Save the updated recently viewed list in the session
    request.session['recently_viewed'] = recently_viewed

    # Fetch a default set of products if the list is empty
    if not recently_viewed:
        default_products = Product.objects.all()[:6]  # Or any criteria for default products
    else:
        default_products = Product.objects.filter(slug__in=recently_viewed)

    # Get the features of the product
    features = Feature.objects.filter(product=product)

    # Get other related objects (optional, as needed)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:6]  # Adjust the filter based on your needs
    sponsored_products = Product.objects.filter(is_sponsored=True)[:6]  # Example, modify as needed
    
    context = {
        'product': product,
        'features': features,
        'related_products': related_products,
        'sponsored_products': sponsored_products,
        'recently_viewed': default_products,
        'seller': seller
    }

    return render(request, 'e-commerce/product_detail.html' , context)
    


from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Category, Product

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category)

    # Apply Pagination (12 Products Per Page)
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    paginated_products = paginator.get_page(page_number)

    return render(request, 'category.html', {
        'category': category,
        'products': paginated_products  # Use paginated products in template
    })


def brand_view(request, slug):
    brand = get_object_or_404(Brand, slug=slug)
    products = Product.objects.filter(brand=brand)
    return render(request, 'brand.html', {'brand': brand, 'products': products})


def account_view(request):
    # Example: You can pass user information like username and email to the template
    user = request.user
    return render(request, 'account.html', {'user': user})

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Product, Cart, CartItem

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 1))
        
        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Check if product already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Added to cart successfully',
                'cart_count': cart.items.count()
            })
        
        # For normal form submission
        messages.success(request, 'Product added to cart successfully!')
        return redirect('cart')
        
    return redirect('product_detail', product_id=product_id)


@login_required
def cart_view(request):
    # Get or create cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get all cart items with their related products
    cart_items = cart.items.select_related('product').all()
    
    # Calculate subtotal
    subtotal = sum(item.subtotal() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
    }
    
    return render(request, 'cart.html', context)

@login_required
def update_cart_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
            
            if action == 'increase':
                cart_item.quantity += 1
            elif action == 'decrease' and cart_item.quantity > 1:
                cart_item.quantity -= 1
            elif action == 'remove':
                cart_item.delete()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Item removed',
                    'cart_subtotal': sum(item.subtotal() for item in request.user.cart.items.all())
                })
            
            cart_item.save()

            # Calculate updated subtotal
            cart_items = CartItem.objects.all()
            cart_subtotal = sum(item.product.price * item.quantity for item in cart_items)
            
            # Return updated cart information
            return JsonResponse({
                'status': 'success',
                'quantity': cart_item.quantity,
                'item_total': cart_item.product.price * cart_item.quantity,
                'cart_subtotal': cart_subtotal
                # 'item_subtotal': cart_item.subtotal(),
                # 'cart_subtotal': sum(item.subtotal() for item in request.user.cart.items.all())
            })
            
        except CartItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def remove_from_cart(request, item_id):
    if request.method == 'POST':
        # Get the cart item, ensuring it belongs to the current user
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        
        # Store the cart reference before deleting the item
        cart = cart_item.cart
        
        # Delete the item
        cart_item.delete()
        
        # Calculate new subtotal
        new_subtotal = sum(item.subtotal() for item in cart.items.all())
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Item removed from cart',
                'cart_subtotal': new_subtotal,
                'cart_count': cart.items.count()
            })
            
        # For regular form submission
        messages.success(request, 'Item removed from cart successfully!')
        return redirect('cart')
        
    # If not POST, redirect to cart
    return redirect('cart')

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem, Order, OrderItem, PickupStation

@login_required
def checkout_view(request):
    user = request.user
    
    # Get user's cart
    cart, created = Cart.objects.get_or_create(user=user)
    cart_items = CartItem.objects.filter(cart=cart)
    
    # Ensure an order exists
    order, created = Order.objects.get_or_create(user=user, status='pending')
    
    # Clear old order items and replace with current cart items
    order.items.all().delete()
    
    # Move cart items to order items
    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.price,  # Store price at the time of order
            vendor=cart_item.product.seller
        )
    
    # Clear cart after moving items to order
    #cart_items.delete()
    
    # Group order items by vendor for shipment display
    shipments = []
    orderitems = order.items.all()
    
    # Example vendors and shipments
    vendors = ['Jumia', 'Prime Classic Investment', 'Blessed GSF']
    delivery_dates = ['20 February', '21 February and 22 February', '21 February and 22 February']
    
    orderitems = order.items.select_related('vendor').all()  # Ensure vendor is prefetched

    # Fetch all unique vendors linked to orders
    vendors = Seller.objects.all()  # Get all vendors dynamically

    shipments = []

    for vendor in vendors:
        vendor_ids = Seller.objects.filter(store_name=vendor.store_name).values_list('id', flat=True)
        
        print(f"Checking vendor: {vendor.store_name}")
        print(f"Vendor IDs: {list(vendor_ids)}")

        vendor_items = orderitems.filter(vendor__id__in=vendor_ids)

        print(f"Vendor Items for {vendor.store_name}: {vendor_items.count()}")

        if vendor_items.exists():
            item = vendor_items.first()
            print(f"Item found: {item.product.name}, Image URL: {item.product.image.url if item.product.image else 'No Image'}")

            shipments.append({
                'fulfilled_by': vendor.store_name,
                'scheduled': False,  # Modify if scheduling logic applies
                'delivery_date': '21 February and 22 February',  # Modify if needed
                'product': item.product,
                'quantity': item.quantity,
                'profile_picture': item.vendor.profile_picture if item.vendor else None
            })




    
    # Assign pickup station
    pickup_station, created = PickupStation.objects.get_or_create(
        name="G4S Makuyu-Kenol Station",
        defaults={
            'location': 'Kenol, Golan House',
            'details': 'Kenol, Golan House, Ground Floor, Muranga - Kenol'
        }
    )
    order.pickup_station = pickup_station
    order.delivery_fee = 461
    order.save()
    
    # Phone display
    phone_display = f"+{user.phone_number}" if user.phone_number else ""
    
    context = {
        'order': {
            'customer_name': f"{user.first_name} {user.last_name}" if user.first_name else user.email,
            'address': user.location,
            'town': 'Muranga Town',
            'phone': phone_display
        },
        'delivery_fee': order.delivery_fee,
        'delivery_start_date': '20 February',
        'delivery_end_date': '22 February',
        'pickup_station': {
            'name': pickup_station.name,
            'location_details': pickup_station.details
        },
        'shipments': shipments,
        'items_total': order.get_cart_total,  # No parentheses
        'order_total': order.get_order_total,  # No parentheses
        'total_items': order.get_total_items  # No parentheses

    }
    
    return render(request, 'checkout2.html', context)


@login_required
def pay_view(request):
    user = request.user
    order = Order.objects.filter(user=user, status='pending').first()

    if not order:
        messages.error(request, "No pending order found.")
        return redirect('checkout_view')

    if request.method == "POST":
        name = request.POST.get("name")
        id_number = request.POST.get("id_number")
        phone_number = request.POST.get("phone_number")

        if not name or not id_number or not phone_number:
            messages.error(request, "All fields are required.")
            return redirect('pay')

        transaction = Transaction.objects.create(
            user=user,
            order=order,
            name=name,
            id_number=id_number,
            phone_number=phone_number,
            amount=order.get_order_total,  # Ensure this returns the correct total
            status="completed"  # Change this based on actual payment processing
        )

        order.status = 'completed'
        order.save()

    
       
        # Get the user's cart and delete the items
        user_cart = Cart.objects.filter(user=user).first()
        if user_cart:
            CartItem.objects.filter(cart=user_cart).delete()

        messages.success(request, "Payment successful! Your order has been placed.")
        return redirect('order_success')

    context = {
        "order_total": order.get_order_total  # Ensure this returns the correct total
    }
    return render(request, "pay.html", context)

def order_success(request):
    return render(request, 'order_success.html')

@login_required
def orders_view(request):
    # Get query parameter for tab selection (default to 'ongoing')
    status = request.GET.get('status', 'ongoing')
    
    # Query the user's orders based on selected tab
    if status == 'canceled':
        orders = Order.objects.filter(
            user=request.user,
            status__in=['CANCELED', 'RETURNED']
        ).order_by('-date_ordered')
        
        # Count for tab display
        canceled_count = orders.count()
        ongoing_count = Order.objects.filter(
            user=request.user,
            status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
        ).count()
    else:
        orders = Order.objects.filter(
            user=request.user,
            status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
        ).order_by('-date_ordered')
        
        # Count for tab display
        ongoing_count = orders.count()
        canceled_count = Order.objects.filter(
            user=request.user,
            status__in=['CANCELED', 'RETURNED']
        ).count()
    
    context = {
        'orders': orders,
        'ongoing_count': ongoing_count,
        'canceled_count': canceled_count
    }
    
    return render(request, 'orders.html', context)

def seller_profile(request, slug):
    seller = get_object_or_404(Seller, slug=slug)
    return render(request, 'seller_profile.html', {'seller': seller})

def search_view(request):
    query = request.GET.get('q', '')
    
    if query:
        # Search products by name (adjust field name if needed)
        results = Product.objects.filter(name__icontains=query)
    else:
        results = Product.objects.all()  # Return all if no query
    
    # Apply pagination (e.g., 10 products per page)
    paginator = Paginator(results, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'search_results.html', {
        'page_obj': page_obj,
        'query': query
    })




#e-commerce admin view 
@login_required
def transaction_list(request):
    """View to display all transactions"""
    # For staff/admin users, show all transactions
    if request.user.is_staff:
        transactions = Transaction.objects.all().order_by('-timestamp')
    # For regular users, show only their transactions
    else:
        transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')
    
    context = {
        'transactions': transactions,
    }
    return render(request, 'transactions/transaction_list.html', context)

@login_required
def transaction_detail(request, transaction_id):
    """View to display details of a specific transaction"""
    # For staff/admin, allow viewing any transaction
    if request.user.is_staff:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    # For regular users, only allow viewing their own transactions
    else:
        transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    
    # Get the order associated with this transaction
    order = transaction.order
    
    # Get all items in this order
    order_items = order.items.all()
    
    context = {
        'transaction': transaction,
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'transactions/transaction_detail.html', context)