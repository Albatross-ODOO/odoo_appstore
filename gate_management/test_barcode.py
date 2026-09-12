try:
    data = env['ir.actions.report'].sudo().barcode('QR', '123456', width=300, height=300)
    print("Barcode generation successful, length:", len(data))
except Exception as e:
    print("Barcode generation failed:", str(e))
