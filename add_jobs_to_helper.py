import json
import ast

def update_replicate_helper():
    # Load JSON
    with open('new_dream_jobs_config.json', 'r') as f:
        dream_jobs = json.load(f)

    # Read the file
    with open('replicate_helper.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find where CHARACTER_STYLES ends
    
    # Simple way: find the exact line
    target = """    'southern_asiri_adult': {
        'prompt': 'Beautiful 25-32 year old Saudi Arabian woman with elegant features and fit body shape, wearing traditional Southern Saudi (Asiri) black dress with vibrant colorful geometric embroidery on the chest and sleeves, yellow headscarf, large ornate golden coin bib necklace, gentle closed-mouth smile, photorealistic, cinematic lighting, historical Saudi courtyard background',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, teeth, open mouth, overweight, bulky',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1771073578/templates/southern_asiri_adult.jpg'
    },
}"""
    
    dict_str = ""
    for k, v in dream_jobs.items():
        dict_str += f"""    '{k}': {{
        'prompt': '{v['prompt']}',
        'negative_prompt': '{v['negative_prompt']}',
        'template_image': '{v['template_image']}'
    }},
"""
    dict_str += "}"

    if target in content:
        new_target = """    'southern_asiri_adult': {
        'prompt': 'Beautiful 25-32 year old Saudi Arabian woman with elegant features and fit body shape, wearing traditional Southern Saudi (Asiri) black dress with vibrant colorful geometric embroidery on the chest and sleeves, yellow headscarf, large ornate golden coin bib necklace, gentle closed-mouth smile, photorealistic, cinematic lighting, historical Saudi courtyard background',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, teeth, open mouth, overweight, bulky',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1771073578/templates/southern_asiri_adult.jpg'
    },
""" + dict_str

        new_content = content.replace(target, new_target)
        
        with open('replicate_helper.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully updated replicate_helper.py")
    else:
        print("Could not find target string in replicate_helper.py")

update_replicate_helper()
