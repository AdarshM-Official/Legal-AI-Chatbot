import sys

with open('core/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the slash quotes
text = text.replace("\\'POST\\'", "'POST'")
text = text.replace("\\'email\\'", "'email'")
text = text.replace("\\'password\\'", "'password'")
text = text.replace("\\'Invalid password.\\'", "'Invalid password.'")
text = text.replace("\\'User not found.\\'", "'User not found.'")
text = text.replace("\\'HTTP_REFERER\\'", "'HTTP_REFERER'")
text = text.replace("\\'/\\'", "'/'")
text = text.replace("\\'name\\'", "'name'")
text = text.replace("\\'Email already exists.\\'", "'Email already exists.'")

with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(text)
