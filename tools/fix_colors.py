import os

replacements = {
    'border-blue-600': 'border-[#c82333]',
    'text-blue-500': 'text-[#c82333]',
    'text-blue-800': 'text-[#a71d2a]',
    'bg-blue-50': 'bg-red-50',
    'bg-blue-100': 'bg-red-100',
    'text-blue-700': 'text-[#c82333]',
    'border-l-blue-400': 'border-l-[#c82333]',
    'hover:text-blue-500': 'hover:text-[#c82333]',
    'border-blue-200': 'border-red-200',
    'text-green-600': 'text-[#c82333]',
    'text-purple-600': 'text-[#c82333]',
    "<img src='https://codeptit.edu.vn/theme/user/images/logo.png' alt='CodePTIT' class='h-10 inline-block'>": "<span class='text-[#c82333] font-bold'>Code</span><span class='text-gray-800 font-bold'>PTIT</span><span class='text-gray-500 font-medium italic'>clone</span>",
}

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for old_str, new_str in replacements.items():
        if old_str in content:
            content = content.replace(old_str, new_str)
            modified = True
            
    # Fix the lightning bolt + image combo
    broken_img_with_bolt = "⚡<span class='text-[#c82333] font-bold'>Code</span>"
    if broken_img_with_bolt in content:
        content = content.replace(broken_img_with_bolt, "<span class='text-[#c82333] font-bold'>Code</span>")
        modified = True
        
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {filepath}')

for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            replace_in_file(os.path.join(root, file))
