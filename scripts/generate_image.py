#!/usr/bin/env python3
"""
Gera uma imagem com SD 1.5 + LCM-LoRA.
Uso: python3 generate_image.py "prompt" /path/output.png
"""
import sys
import os
import warnings
warnings.filterwarnings("ignore")


def main():
    if len(sys.argv) < 3:
        print("Uso: generate_image.py <prompt> <output_path>", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    output_path = sys.argv[2]

    from diffusers import DiffusionPipeline, LCMScheduler
    import torch

    pipe = DiffusionPipeline.from_pretrained(
        "stable-diffusion-v1-5/stable-diffusion-v1-5",
        torch_dtype=torch.float32,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)

    image = pipe(
        prompt=prompt,
        num_inference_steps=4,
        guidance_scale=1.0,
        width=512,
        height=512,
    ).images[0]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    image.save(output_path)
    print(f"OK: {output_path}")


if __name__ == "__main__":
    main()
