import json
from pathlib import Path

import config
from services.payment_service import PaymentService
from services.pix_generator import PIXGenerator


def test_config_data_paths():
    assert config.PAID_USERS_FILE == str(Path(config.DATA_DIR) / "paid_users.json")
    assert config.PIX_MAPPINGS_FILE == str(Path(config.DATA_DIR) / "pix_mappings.json")
    assert Path(config.DATA_DIR).exists()


def test_paid_users_persist_across_instances(tmp_path):
    paid_file = tmp_path / "paid_users.json"
    svc1 = PaymentService(data_file=str(paid_file))
    assert svc1.confirm_payment(999888777) is True
    assert svc1.is_paid_user(999888777)

    svc2 = PaymentService(data_file=str(paid_file))
    assert svc2.is_paid_user(999888777)


def test_pending_payment_saved_to_disk(tmp_path):
    paid_file = tmp_path / "paid_users.json"
    svc = PaymentService(data_file=str(paid_file))
    svc.register_pending_payment(111222333, amount=20.0, product_id="gpt_premium")

    with open(paid_file, encoding="utf-8") as f:
        saved = json.load(f)

    assert "111222333" in saved["pending_payments"]
    assert saved["pending_payments"]["111222333"]["amount"] == 20.0


def test_pix_mappings_persist_across_instances(tmp_path):
    mapping_file = tmp_path / "pix_mappings.json"
    gen1 = PIXGenerator(mapping_file=str(mapping_file))
    gen1.payment_to_user["pay123"] = 555666777
    gen1.user_to_payment[555666777] = "pay123"
    gen1._save_mappings()

    gen2 = PIXGenerator(mapping_file=str(mapping_file))
    assert gen2.get_user_by_payment_id("pay123") == 555666777
    assert gen2.get_payment_id_by_user(555666777) == "pay123"


def test_docker_default_data_dir():
    """Com DATA_DIR=/app/data, arquivos ficam no volume persistente."""
    data_dir = "/app/data"
    paid_file = str(Path(data_dir) / "paid_users.json")
    pix_file = str(Path(data_dir) / "pix_mappings.json")
    assert paid_file.replace("\\", "/") == "/app/data/paid_users.json"
    assert pix_file.replace("\\", "/") == "/app/data/pix_mappings.json"
