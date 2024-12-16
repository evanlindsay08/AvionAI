from aiohttp import web, ClientSession
import json
import os
from dotenv import load_dotenv
import requests
import time
import pathlib

load_dotenv()

routes = web.RouteTableDef()
LEONARDO_API_KEY = os.getenv('LEONARDO_API_KEY')
LEONARDO_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

ART_STYLE_PROMPTS = {
    'pixel': """16-bit pixel art style, retro gaming aesthetic, clean pixelated edges,
        reminiscent of classic video games, limited color palette, sharp pixels""",
    'anime': """anime art style, manga-inspired, cel-shaded, vibrant colors,
        kawaii aesthetic, clean linework, anime character design""",
    '3d': """3D rendered style, volumetric lighting, subsurface scattering,
        realistic textures, ambient occlusion, ray-traced reflections""",
    'minimalist': """minimalist design, clean lines, simple shapes,
        limited color palette, negative space, geometric composition""",
    'cartoon': """cartoon style, bold outlines, vibrant colors,
        exaggerated features, playful design, smooth shading""",
    'realistic': """realistic digital painting, detailed textures,
        professional illustration, photorealistic elements, detailed shading"""
}

BASE_DIR = pathlib.Path(__file__).parent

@routes.get('/')
async def serve_html(request):
    try:
        with open(BASE_DIR / 'index.html', 'r') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.post('/api/generate')
async def generate(request):
    try:
        data = await request.json()
        print("Received data:", data)
        idea = data.get('idea')
        art_style = data.get('artStyle', 'pixel')
        
        print(f"Processing request - idea: {idea}, style: {art_style}")

        if not idea:
            return web.json_response({"error": "No idea provided"}, status=400)

        # Get the art style prompt
        style_prompt = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS['pixel'])

        # Create base prompt
        base_prompt = f"""detailed cryptocurrency mascot logo of a {idea},
            {style_prompt},
            centered composition, clean vectorized style,
            suitable for crypto token, professional logo design"""

        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {LEONARDO_API_KEY}',
            'content-type': 'application/json'
        }

        payload = {
            "height": 512,
            "width": 512,
            "prompt": base_prompt,
            "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",
            "negative_prompt": "text, watermark, logo, words, letters, signature, realistic, photographic, abstract shapes, blurry, low quality",
            "num_images": 1,
            "guidance_scale": 8,
            "init_strength": 0.4
        }

        try:
            print(f"Making request to Leonardo API...")
            
            async with ClientSession() as session:
                async with session.post(
                    f"{LEONARDO_BASE_URL}/generations",
                    headers=headers,
                    json=payload
                ) as response:
                    response_text = await response.text()
                    print(f"Response status: {response.status}")
                    print(f"Response text: {response_text}")
                    
                    if response.status != 200:
                        return web.json_response(
                            {"error": f"Failed to generate image: {response_text}"}, 
                            status=response.status
                        )
                    
                    generation_data = json.loads(response_text)
                    generation_id = generation_data['sdGenerationJob']['generationId']
                    
                    # Poll for results
                    for _ in range(30):
                        async with session.get(
                            f"{LEONARDO_BASE_URL}/generations/{generation_id}",
                            headers=headers
                        ) as check_response:
                            if check_response.status == 200:
                                result = await check_response.json()
                                if result['generations_by_pk']['status'] == 'COMPLETE':
                                    image_url = result['generations_by_pk']['generated_images'][0]['url']
                                    return web.json_response({
                                        'imageUrl': image_url,
                                        'name': idea.title(),
                                        'ticker': ''.join(word[0].upper() for word in idea.split()[:3]),
                                        'description': f"Revolutionary {idea} token powered by advanced AI technology.",
                                        'socialLinks': ['Twitter Account', 'Telegram Group', 'Website'],
                                        'success': True
                                    })
                        await web.asyncio.sleep(1)

                    return web.json_response({"error": "Timeout waiting for image"}, status=500)

        except Exception as api_error:
            print(f"API request error: {str(api_error)}")
            return web.json_response(
                {"error": f"API request failed: {str(api_error)}"}, 
                status=500
            )

    except Exception as e:
        print(f"Detailed error: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

@routes.get('/home')
async def serve_home(request):
    try:
        with open(BASE_DIR / 'home.html', 'r') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.get('/generator')
async def serve_generator(request):
    try:
        with open(BASE_DIR / 'generator.html', 'r') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.get('/whitepaper')
async def serve_whitepaper(request):
    try:
        with open(BASE_DIR / 'whitepaper.html', 'r') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.get('/assets/{filename}')
async def serve_assets(request):
    filename = request.match_info['filename']
    try:
        with open(BASE_DIR / 'assets' / filename, 'rb') as f:
            return web.Response(body=f.read(), content_type='image/png')
    except Exception as e:
        return web.Response(text=str(e), status=500)

if __name__ == '__main__':
    print("Starting server...")
    print(f"Leonardo API Key present: {'Yes' if LEONARDO_API_KEY else 'No'}")
    port = int(os.environ.get('PORT', 8000))
    web.run_app(web.Application().add_routes(routes), port=port, host='0.0.0.0') 