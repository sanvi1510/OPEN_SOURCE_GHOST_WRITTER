from tools.docker_executor import run_code_in_sandbox

result = run_code_in_sandbox("print('hello world')")
print(result)