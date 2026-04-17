import re

def resolve_test_cli():
    with open("tests/test_cli.py", "r") as f:
        src = f.read()
    
    def repl(m):
        head = m.group(1).strip()
        theirs = m.group(2).strip()
        # They are separate tests, keep both
        return f"{head}\n\n{theirs}\n"
    
    src = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> 53ee[\w]+', repl, src, flags=re.DOTALL)
    with open("tests/test_cli.py", "w") as f:
        f.write(src)

def resolve_exposure():
    with open("src/apcore_cli/exposure.py", "r") as f:
        src = f.read()
    
    def repl(m):
        return m.group(2) # Keep theirs
    
    src = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> 53ee[\w]+', repl, src, flags=re.DOTALL)
    with open("src/apcore_cli/exposure.py", "w") as f:
        f.write(src)

def resolve_main():
    # Only their refactored code should remain
    with open("src/apcore_cli/__main__.py", "r") as f:
        src = f.read()
        
    def repl(m):
        return m.group(2) # Keep theirs
    
    src = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> 53ee[\w]+', repl, src, flags=re.DOTALL)
    with open("src/apcore_cli/__main__.py", "w") as f:
        f.write(src)

resolve_test_cli()
resolve_exposure()
resolve_main()
