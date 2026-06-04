# -*- coding: utf-8 -*-
"""
Prueba completa del extractor sobre el PDF de muestra.
"""
import fitz
from extractor import process_pdf_page

def main():
    doc = fitz.open("Cosas/20260604142405.pdf")
    print(f"Abierto PDF de muestra con {len(doc)} páginas.")
    
    total_articles = 0
    unresolved_treatments = set()
    pages_with_problems = 0
    
    for i in range(len(doc)):
        page = doc[i]
        res = process_pdf_page(page, i+1)
        
        # Conteo
        total_articles += len(res["articles"])
        if res["had_problem"]:
            pages_with_problems += 1
            for p in res["problem_details"]:
                # extract raw treatment
                pass
                
        for art in res["articles"]:
            if art["needs_resolution"]:
                unresolved_treatments.add(art["treatment_raw"])
                
        # Mostrar detalle de algunas páginas específicas para validar
        if i+1 in [1, 9, 13, 22, 40, 75]:
            print(f"\n--- Detalle Página {i+1} ---")
            print(f"Pedido: {res['order_number']} | Fecha: {res['date']} | Cliente: {res['client']}")
            print(f"Artículos ({len(res['articles'])}):")
            for art in res["articles"]:
                print(f"  - Cód: {art['code']} | Cant: {art['quantity']} | Desc: {art['description']} | Trat: {art['treatment_mapped']} (Raw: '{art['treatment_raw']}')")
                
    print("\n=== Resumen de Prueba ===")
    print(f"Total páginas procesadas: {len(doc)}")
    print(f"Total artículos extraídos: {total_articles}")
    print(f"Páginas con problemas (tratamientos desconocidos): {pages_with_problems}")
    print(f"Tratamientos desconocidos únicos ({len(unresolved_treatments)}): {unresolved_treatments}")

if __name__ == "__main__":
    main()
