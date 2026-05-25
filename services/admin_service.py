# /app/services/admin_service.py

class AdminService:
    def is_initialized(self):
        # La tua logica qui
        return True 

    def create_admin(self, data):
        # La tua logica qui
        pass

# QUESTA RIGA È OBBLIGATORIA
# Senza questa, 'admin_service' non esiste come oggetto importabile
admin_service = AdminService()
