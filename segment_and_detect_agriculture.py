import os
import torch
import torch.nn.functional as F
from PIL import Image
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
from transformers import SegformerConfig, SegformerForSemanticSegmentation
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import shutil

# ==================== Settings ====================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = "/home/arda/Masaüstü/SP-494/Video_Output/best_segformer_b3_ema_.pth"  # Model weight file

# ==================== Image Transformations ====================
transform = A.Compose([
    A.Resize(512, 512),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2()
])

def unnormalize(img_tensor):
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1).to(img_tensor.device)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1).to(img_tensor.device)
    return img_tensor * std + mean

def refine_agriculture_class(pred_mask):
    refined = pred_mask.clone()
    h, w = refined.shape
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            if refined[i, j] == 1:
                local_patch = refined[i-1:i+2, j-1:j+2]
                if (local_patch == 5).sum() >= 3:
                    refined[i, j] = 5
    return refined

label_colors = {
    0: (0, 0, 0),
    1: (255, 0, 0),
    2: (255, 255, 0),
    3: (0, 255, 255),
    4: (0, 0, 255),
    5: (139, 69, 19),
    6: (0, 128, 0),
}

label_names = {
    0: "Background",
    1: "Other",
    2: "Building",
    3: "Road",
    4: "Water",
    5: "Agriculture",
    6: "Forest"
}

def mask_has_agriculture(mask_arr, agriculture_label=5):
    """Checks if the agriculture label is present in the numpy mask."""
    return (mask_arr == agriculture_label).any()

def process_frames(input_dir, output_dir, agriculture_detect_dir=None, frames_original_dir=None):
    os.makedirs(output_dir, exist_ok=True)
    if agriculture_detect_dir is not None:
        os.makedirs(agriculture_detect_dir, exist_ok=True)
    if frames_original_dir is not None:
        os.makedirs(frames_original_dir, exist_ok=True)

    frame_files = sorted([
        f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    # ==================== Model Loading ====================
    config = SegformerConfig.from_pretrained("nvidia/segformer-b3-finetuned-ade-512-512")
    config.num_labels = 7
    model = SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/segformer-b3-finetuned-ade-512-512",
        config=config,
        ignore_mismatched_sizes=True
    ).to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()

    for image_name in frame_files:
        image_path = os.path.join(input_dir, image_name)
        img_pil = Image.open(image_path).convert("RGB")
        img_np = np.array(img_pil)
        transformed = transform(image=img_np)["image"].unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            img_flip = torch.flip(transformed, dims=[3])
            out1 = model(transformed).logits
            out2 = model(img_flip).logits
            out2 = torch.flip(out2, dims=[3])
            output = (out1 + out2) / 2
            pred_mask = output.argmax(dim=1)[0]

        refined_small = refine_agriculture_class(pred_mask.cpu())
        refined_resized = F.interpolate(
            refined_small.unsqueeze(0).unsqueeze(0).float(), size=(512, 512), mode='nearest'
        ).squeeze().long()

        # Color the mask
        pred_rgb = np.zeros((512, 512, 3), dtype=np.uint8)
        for cls_id, color in label_colors.items():
            pred_rgb[refined_resized == cls_id] = color

        # Unnormalize original image
        unnorm = unnormalize(transformed[0]).permute(1, 2, 0).cpu().numpy()

        # ========== Save with matplotlib ==========
        fig, axs = plt.subplots(1, 3, figsize=(18, 8), gridspec_kw={'width_ratios': [3, 3, 1]})
        axs[0].imshow(np.clip(unnorm, 0, 1))
        axs[0].set_title(f"Input: {image_name}")
        axs[0].axis("off")

        axs[1].imshow(pred_rgb)
        axs[1].set_title("Refined Prediction")
        axs[1].axis("off")

        legend_patches = [
            mpatches.Patch(color=np.array(color)/255.0, label=label_names[cls_id])
            for cls_id, color in label_colors.items()
        ]
        axs[2].legend(handles=legend_patches, loc="center left", fontsize=10)
        axs[2].axis("off")
        axs[2].set_title("Legend")

        plt.tight_layout()
        save_path = os.path.join(output_dir, f"{os.path.splitext(image_name)[0]}_viz.png")
        plt.savefig(save_path)
        plt.close(fig)
        print(f"[INFO] Kayıt yapıldı: {save_path}")

        # --- Copy the frames containing Agriculture to a separate folder ---
        if agriculture_detect_dir is not None and frames_original_dir is not None:
            # Check mask (use mask's label array)
            if mask_has_agriculture(refined_resized.numpy(), agriculture_label=5):
                # Copy the first mask (its visualized form).
                dest_mask_path = os.path.join(agriculture_detect_dir, os.path.basename(save_path))
                shutil.copy(save_path, dest_mask_path)
                # Also copy the second original frame.
                dest_img_path = os.path.join(frames_original_dir, image_name)
                shutil.copy(image_path, dest_img_path)
                print(f"[INFO] Agriculture detected: {image_name} ({dest_mask_path})")

if __name__ == "__main__":
    # First Video
    process_frames(
        input_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_1_frames",
        output_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_1_detect",
        agriculture_detect_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_1_Agriculture_detect",
        frames_original_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_1_Agriculture_frames"
    )
    # 2.Second Video
    process_frames(
        input_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_2_frames",
        output_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_2_detect",
        agriculture_detect_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_2_Agriculture_detect",
        frames_original_dir="/home/arda/Masaüstü/SP-494/Video_Output/output_video_2_Agriculture_frames"
    )
