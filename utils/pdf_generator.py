# utils/pdf_generator.py

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import logging

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self):
        self.reports_dir = 'reports'
        os.makedirs(self.reports_dir, exist_ok=True)
        
    def generate_report(self, disease, treatment, confidence=0, severity='Unknown', ai_generated=False):
        """Generate a comprehensive PDF report"""
        try:
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'agrisage_report_{timestamp}.pdf'
            filepath = os.path.join(self.reports_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )
            
            # Container for the 'Flowable' objects
            elements = []
            
            # Define styles
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#667eea'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#333333'),
                spaceAfter=12,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#555555'),
                alignment=TA_JUSTIFY,
                spaceAfter=12
            )
            
            # Add Title
            elements.append(Paragraph("🌱 AgriSage - Crop Disease Analysis Report", title_style))
            elements.append(Spacer(1, 20))
            
            # Add Report Info
            report_info = [
                ['Report Date:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
                ['Analysis Method:', 'AI-Powered Detection' if ai_generated else 'Standard Detection'],
                ['Report ID:', f'AGS-{timestamp}']
            ]
            
            info_table = Table(report_info, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0'))
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 30))
            
            # Disease Detection Results
            elements.append(Paragraph("📊 Disease Detection Results", heading_style))
            elements.append(Spacer(1, 10))
            
            # Create results table
            results_data = [
                ['Disease Detected:', disease or 'Unknown'],
                ['Confidence Level:', f'{confidence}%' if confidence else 'N/A'],
                ['Severity:', severity],
                ['Risk Level:', self._get_risk_level(confidence)]
            ]
            
            results_table = Table(results_data, colWidths=[2*inch, 4*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('BACKGROUND', (1, 0), (1, -1), colors.white),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0'))
            ]))
            elements.append(results_table)
            elements.append(Spacer(1, 30))
            
            # Treatment Recommendations
            if treatment:
                elements.append(Paragraph("💊 Treatment Recommendations", heading_style))
                elements.append(Spacer(1, 15))
                
                # Organic Treatment
                if treatment.get('organic'):
                    elements.append(Paragraph("🌿 <b>Organic Treatment Options:</b>", normal_style))
                    for item in treatment['organic'][:5]:  # Limit to 5 items
                        bullet_text = f"• {item}"
                        elements.append(Paragraph(bullet_text, normal_style))
                    elements.append(Spacer(1, 15))
                
                # Chemical Treatment
                if treatment.get('chemical'):
                    elements.append(Paragraph("⚗️ <b>Chemical Treatment Options:</b>", normal_style))
                    for item in treatment['chemical'][:5]:  # Limit to 5 items
                        bullet_text = f"• {item}"
                        elements.append(Paragraph(bullet_text, normal_style))
                    elements.append(Spacer(1, 15))
                
                # Prevention Methods
                if treatment.get('prevention'):
                    elements.append(Paragraph("🛡️ <b>Prevention Methods:</b>", normal_style))
                    for item in treatment['prevention'][:5]:  # Limit to 5 items
                        bullet_text = f"• {item}"
                        elements.append(Paragraph(bullet_text, normal_style))
                    elements.append(Spacer(1, 15))
                
                # Immediate Actions
                if treatment.get('immediate_actions') and len(treatment['immediate_actions']) > 0:
                    elements.append(Paragraph("⚠️ <b>Immediate Actions Required:</b>", normal_style))
                    for item in treatment['immediate_actions'][:3]:  # Limit to 3 items
                        bullet_text = f"• {item}"
                        elements.append(Paragraph(bullet_text, normal_style))
                    elements.append(Spacer(1, 15))
            
            # Add Recommendations Section
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("📝 General Recommendations", heading_style))
            elements.append(Spacer(1, 10))
            
            recommendations = [
                "• Regularly monitor your crops for any changes in symptoms",
                "• Maintain proper field sanitation and remove infected plant debris",
                "• Ensure adequate spacing between plants for air circulation",
                "• Follow integrated pest management (IPM) practices",
                "• Keep records of treatments applied and their effectiveness",
                "• Consult with local agricultural experts for severe cases"
            ]
            
            for rec in recommendations:
                elements.append(Paragraph(rec, normal_style))
            
            # Add Footer
            elements.append(Spacer(1, 40))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#888888'),
                alignment=TA_CENTER
            )
            
            elements.append(Paragraph("─" * 50, footer_style))
            elements.append(Paragraph(
                "This report is generated by AgriSage AI System. For best results, "
                "combine these recommendations with local agricultural expertise.",
                footer_style
            ))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(
                "© 2024 AgriSage - Empowering Farmers with AI",
                footer_style
            ))
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"PDF report generated successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            # Create a simple fallback PDF
            return self._create_fallback_pdf(disease, treatment, confidence)
    
    def _get_risk_level(self, confidence):
        """Determine risk level based on confidence"""
        if confidence >= 80:
            return "High Risk - Immediate Action Required"
        elif confidence >= 60:
            return "Medium Risk - Monitor Closely"
        elif confidence >= 40:
            return "Low Risk - Preventive Measures Advised"
        else:
            return "Uncertain - Further Inspection Needed"
    
    def _create_fallback_pdf(self, disease, treatment, confidence):
        """Create a simple fallback PDF if main generation fails"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'agrisage_report_{timestamp}.pdf'
            filepath = os.path.join(self.reports_dir, filename)
            
            # Create a simple PDF with basic info
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            c = canvas.Canvas(filepath, pagesize=letter)
            width, height = letter
            
            # Title
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height - 50, "AgriSage Disease Report")
            
            # Content
            c.setFont("Helvetica", 12)
            y_position = height - 100
            
            # Disease info
            c.drawString(50, y_position, f"Disease Detected: {disease or 'Unknown'}")
            y_position -= 25
            c.drawString(50, y_position, f"Confidence: {confidence}%")
            y_position -= 25
            c.drawString(50, y_position, f"Date: {datetime.now().strftime('%B %d, %Y')}")
            y_position -= 40
            
            # Treatment info
            if treatment:
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y_position, "Treatment Recommendations:")
                y_position -= 25
                
                c.setFont("Helvetica", 11)
                
                # Add organic treatments
                if treatment.get('organic'):
                    c.drawString(50, y_position, "Organic Treatment:")
                    y_position -= 20
                    for item in treatment['organic'][:3]:
                        if y_position < 100:
                            break
                        c.drawString(70, y_position, f"• {item[:80]}")
                        y_position -= 18
                    y_position -= 10
                
                # Add chemical treatments
                if treatment.get('chemical') and y_position > 150:
                    c.drawString(50, y_position, "Chemical Treatment:")
                    y_position -= 20
                    for item in treatment['chemical'][:3]:
                        if y_position < 100:
                            break
                        c.drawString(70, y_position, f"• {item[:80]}")
                        y_position -= 18
            
            # Footer
            c.setFont("Helvetica", 9)
            c.drawCentredString(width/2, 30, "© 2024 AgriSage - AI-Powered Farming Assistant")
            
            c.save()
            logger.info(f"Fallback PDF created: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to create fallback PDF: {str(e)}")
            raise

# Create a global instance
pdf_generator = PDFGenerator()