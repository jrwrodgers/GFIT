PYTHON TERMINAL>>>
import torch
torch.cuda.is_available()


SHELL>>>
.\.venv\Scripts\activate
pip3 install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126


import torch
print(torch.version.cuda)
print(torch.cuda.get_device_name(0))
print(torch.cuda.get_device_capability(0)