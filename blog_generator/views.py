from django.shortcuts import render,redirect   
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
import os
from .models import BlogPost
from openai import OpenAI
import re
from dotenv import load_dotenv
import google.generativeai as genai
from .utils import get_gemini_transcript

# Create your views here.
load_dotenv()


@login_required
def index(request):
    recent_blogs = BlogPost.objects.filter(user=request.user).order_by('-id')
    return render(request, 'index.html', {'recent_blogs': recent_blogs})

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            # Validate user authentication
            if not request.user.is_authenticated:
                print("[ERROR] Unauthenticated access attempt")
                return JsonResponse({'error': 'Authentication required'}, status=401)
                
            # Parse and validate input
            try:
                data = json.loads(request.body)
                yt_link = data.get('link', '').strip()
                
                if not yt_link:
                    print("[ERROR] Empty YouTube link")
                    return JsonResponse({'error': 'YouTube link is required'}, status=400)
                    
            except json.JSONDecodeError:
                print("[ERROR] Invalid JSON data")
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
                
            # Get YouTube title
            title, transcription = get_gemini_transcript(yt_link)
            
            if not title or not transcription:
                print("[ERROR] Gemini failed to get title/transcript")
                return JsonResponse({'error': 'Failed to process YouTube video'}, status=500)
            
            # Generate blog content
            blog_content = generate_blog_from_transcription(transcription)
            if not blog_content:
                print("[ERROR] Blog content generation failed")
                return JsonResponse({'error': 'Failed to generate blog article'}, status=500)
            
            # Clean content
            cleaned_content = re.sub(
                r'\{%\s*static\s*[\'"][^\'"]+[\'"]\s*%\}', 
                '', 
                blog_content
            )
            # Create and save blog post
            new_blog_article = BlogPost.objects.create(
                user=request.user,
                youtube_title=title,
                youtube_link=yt_link,
                generated_content=cleaned_content,
            )
            print(f"[SUCCESS] BlogPost created: ID {new_blog_article.id}")
            
            return JsonResponse({
                'content': cleaned_content,
                'success': 'Blog post generated successfully',
                'post_id': new_blog_article.id
            })
            
        except Exception as e:
            print(f"[CRITICAL ERROR] generate_blog: {str(e)}")
            return JsonResponse({
                'error': f'Content generation failed: {str(e)}'
            }, status=500)
            
    print("[ERROR] Non-POST request received")
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
def generate_blog_from_transcription(transcription):
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("[CRITICAL] Missing PERPLEXITY_API_KEY")
        return None

    try:
        # Create client with timeout configuration
        client = OpenAI(
            api_key=api_key, 
            base_url="https://api.perplexity.ai",
            timeout=30  # Set timeout for API requests
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a technical content writer creating blog articles EXCLUSIVELY from provided transcripts. "
                    "STRICTLY follow these rules:\n"
                    "1. NEVER mention video, transcript, or YouTube\n"
                    "2. NEVER discuss tools/extensions unless explicitly in the transcript\n"
                    "3. Output ONLY english-text-formatted content without markdown\n"
                    "4. Structure content as: <h2>Section</h2><p>Content</p> but the tags should not be there in the final created content. the generated content will be add as innerText so do accoridngly.\n"
                    "5. Use ONLY information from the transcript - no external knowledge\n"
                    "6. Avoid any Django-specific terminology unless present in transcript"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Create a comprehensive blog article using ONLY this content:\n\n"
                    f"### TRANSCRIPT START ###\n"
                    f"{transcription}\n"
                    f"### TRANSCRIPT END ###\n\n"
                    f"Requirements:\n"
                    f"- Convert technical explanations into educational content\n"
                    f"- Maintain original concepts but rewrite professionally\n"
                    f"- Never reveal you're working from a transcript\n"
                    f"- Minimum 4 paragraphs with headings\n"
                    f"- Output pure text without {{% static %}} tags"
                ),
            }
        ]

        response = client.chat.completions.create(
            model="sonar-pro",  
            messages=messages,
            max_tokens=1000,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"[ERROR] Content generation failed: {str(e)}")
        return None
       
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password = password)
        
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or Password'
            return render(request, 'login.html', {'error_message': error_message})
    return render(request, 'login.html')


def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']
        
        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message': error_message })
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message': error_message })
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect("/")