import torch, torchvision
print("Torch version:", torch.__version__)
print("Torchvision version:", torchvision.__version__)
print("cuda available:", torch.cuda.is_available())
print("Number of GPUs:", torch.cuda.device_count())

# Test torchvision.ops.nms
boxes = torch.tensor([[0,0,10,10],[1,1,11,11]], dtype=torch.float32).cuda()
scores = torch.tensor([0.9, 0.8], dtype=torch.float32).cuda()
kept = torchvision.ops.nms(boxes, scores, iou_threshold=0.5)
print("NMS result:", kept)
