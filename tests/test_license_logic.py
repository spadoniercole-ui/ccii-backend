# Crea un file: tests/test_license_logic.py
from datetime import date, timedelta
from services.admin_service import admin_service
# ... import mock session ...

def test_validate_license_expiration():
    # Creiamo una licenza scaduta
    mock_licenza = Licenza(data_scadenza=date.today() - timedelta(days=1))
    
    # Verifichiamo che il servizio lanci l'eccezione giusta
    try:
        admin_service.validate_license_and_create_space(..., licenza=mock_licenza)
    except HTTPException as e:
        assert e.status_code == 400
        assert "scaduta" in e.detail
