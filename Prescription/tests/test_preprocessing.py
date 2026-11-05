from PIL import Image, ImageDraw

from src.preprocessing import preprocess_prescription


def _sample_prescription() -> Image.Image:
    image = Image.new("RGB", (900, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 860, 560), outline="#1a7a7a", width=3)
    draw.text((70, 70), "Dr. A. Sharma  MD", fill="#111111")
    draw.text((70, 120), "Patient: Test User", fill="#111111")
    draw.text((70, 180), "Rx", fill="#111111")
    draw.text((90, 230), "Amoxicillin 500 mg", fill="#111111")
    draw.text((90, 270), "1 cap TDS x 5 days  PO", fill="#111111")
    draw.text((90, 330), "Pantoprazole 40 mg", fill="#111111")
    draw.text((90, 370), "1 tab OD before breakfast", fill="#111111")
    return image


def test_preprocess_keeps_size_and_produces_stages():
    result = preprocess_prescription(_sample_prescription())
    assert result.grayscale.ndim == 2
    assert result.clahe.shape == result.grayscale.shape
    assert result.deskewed.shape == result.grayscale.shape
    assert result.thresholded.shape == result.grayscale.shape
    assert result.model_input.shape[2] == 3
    assert result.original_bgr.shape[0] == 600
    ink_ratio = (result.thresholded < 250).mean()
    assert 0.001 < ink_ratio < 0.5
