def get_review_request_email(customer_name, product_name, review_link):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background: #f8fafc; }}
            .button {{ background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; }}
            .footer {{ text-align: center; padding: 20px; color: #64748b; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🛡️ ReviewShield</h2>
            </div>
            <div class="content">
                <h3>Hello {customer_name}! 👋</h3>
                <p>Thank you for purchasing <strong>{product_name}</strong> from us!</p>
                <p>We would love to hear about your experience. Please take a moment to share your feedback.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{review_link}" class="button">📝 Write a Review</a>
                </div>
                <p>Your feedback helps us improve and helps other customers make informed decisions.</p>
                <p>⭐ ⭐ ⭐ ⭐ ⭐</p>
            </div>
            <div class="footer">
                <p>You received this email because you made a purchase from us.</p>
                <p>ReviewShield - AI-Powered Review Management</p>
            </div>
        </div>
    </body>
    </html>
    """