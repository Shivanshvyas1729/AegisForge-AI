# CHENNAI PETROLEUM / GUWAHATI REFINERY QUALITY ASSURANCE
## METALLURGICAL & NON-DESTRUCTIVE TESTING (NDT) LABORATORY
### STATUTORY INSPECTION REPORT: ULTRASONIC THICKNESS SURVEY (API 510 / API 572)

**Report No:** NDT/HCU/2026/UT-9021  
**Date of Inspection:** 04th September 2026  
**Plant Unit:** Hydrocracker Unit (HCU-11)  
**Equipment Name:** 1st Stage Hydrocracker Reactor Effluent Separator (`11-V-102`)  
**Statutory Code:** API 510 (Pressure Vessel Inspection Code) & ASME Section V Article 5  
**Service:** High-Pressure Wet $\text{H}_2\text{S}$ + Hydrogen Hydrocarbon Slurry ($145\text{ barg}$, $285^\circ\text{C}$)  
**Inspection Technique:** Multi-channel Digital Ultrasonic Thickness Gauge (Olympus 38DL Plus) with $5.0\text{ MHz}$ High-Temp Delay Line Transducer  
**Surface Preparation:** Grit Blasting to Sa 2.5 standard  

---

### 1. VESSEL TECHNICAL SPECIFICATIONS
- **Fabrication Drawing No:** GHR-VES-11-V-102-M01
- **Design Pressure:** $14.50\text{ MPa}$ ($145.0\text{ barg}$)
- **Design Temperature:** $285^\circ\text{C}$
- **Base Metal:** Low-Alloy Chrome-Moly Steel ($2.25\text{Cr}-1\text{Mo}$ per SA-387 Gr 22 Cl 2)
- **Internal Cladding:** $3.0\text{ mm}$ Weld Overlay Type 347 Stainless Steel
- **Original Nominal Thickness ($t_{\text{nom}}$):** $145.00\text{ mm}$
- **Minimum Allowable Thickness ($t_{\text{min}}$ per ASME Sec VIII Calc):** **$138.57\text{ mm}$**
- **Original Corrosion Allowance ($CA$):** $4.00\text{ mm}$
- **Commissioning Date:** April 2012 (Active Service: 14.4 Years)

---

### 2. ULTRASONIC GRID THICKNESS READINGS (C-SCAN TEST MATRIX)

Ultrasonic thickness readings were measured across an indexed 8-point radial grid ($0^\circ, 90^\circ, 180^\circ, 270^\circ$) at 4 elevation levels (Top Head, Upper Shell Course C-1, Middle Shell Course C-2, Bottom Knuckle):

| Location ID | Inspection Point Description | Baseline 2012 ($t_0$) | Last Turnaround 2022 | Current Reading 2026 ($t_{\text{actual}}$) | Loss from Baseline (mm) | Short-Term Corrosion Rate (mm/yr) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TH-01** | Top Head Knuckle (Crown) | 140.20 mm | 139.80 mm | 139.60 mm | 0.60 mm | 0.050 mm/yr |
| **SC-1A** | Upper Shell Course C-1 (0° North) | 145.10 mm | 143.20 mm | 142.40 mm | 2.70 mm | 0.200 mm/yr |
| **SC-1B** | Upper Shell Course C-1 (180° South) | 145.05 mm | 143.10 mm | 142.15 mm | 2.90 mm | 0.237 mm/yr |
| **SC-2A** | Middle Shell Course C-2 (90° East) | 145.20 mm | 142.50 mm | 141.20 mm | 4.00 mm | 0.325 mm/yr |
| **SC-2B** | Middle Shell Course C-2 (270° West) | 145.15 mm | 142.40 mm | 141.05 mm | 4.10 mm | 0.337 mm/yr |
| **BK-01** | Bottom Dish Knuckle (Vapor Inlet Impingement) | 145.00 mm | 141.20 mm | **138.20 mm** | **6.80 mm** | **0.750 mm/yr** |
| **BK-02** | Liquid Sump Drain Nozzle Neck | 144.80 mm | 142.00 mm | 140.10 mm | 4.70 mm | 0.475 mm/yr |

---

### 3. DEFECT ANALYSIS & REMAINING SERVICE LIFE CALCULATION

#### 3.1 Critical Excursion at Bottom Knuckle Point `BK-01`:
- Current Measured Thickness: **$138.20\text{ mm}$**
- Code Minimum Required Thickness ($t_{\text{min}}$): **$138.57\text{ mm}$**
- **Condition:** Measured thickness has breached the ASME Section VIII design minimum by **$-0.37\text{ mm}$**! The entire 4.0 mm corrosion allowance plus 0.37 mm of base metal has been consumed due to localized sour gas turbulent impingement.

#### 3.2 Remaining Life Formula (API 510 Section 7.1.1):
$$\text{Remaining Life (Years)} = \frac{t_{\text{actual}} - t_{\text{min}}}{\text{Corrosion Rate}}$$
For Point `BK-01`:
$$\text{Remaining Life} = \frac{138.20 - 138.57}{0.750} = \mathbf{-0.49\text{ Years (EXPIRED)}}$$

#### 3.3 Ultrasonic Flaw Detection (Shear Wave Angle Beam 45°/60°):
- Longitudinal Weld Seam L-1 adjacent to `BK-01` exhibited High-Temperature Hydrogen Attack (HTHA) micro-fissuring indications (Chauvelon echo attenuation, severity Class 3).

---

### 4. MANDATORY INSPECTION DISPOSITION & RECOMMENDATIONS
> [!CAUTION]
> **STATUTORY SAFETY DERATING / IMMEDIATE ACTION REQUIRED**
> Point `BK-01` of vessel `11-V-102` is operating in violation of API 510 and PESO statutory safety margins. Continued operation at full design pressure ($145\text{ barg}$) presents risk of catastrophic rupture.

1. **Immediate Pressure Derating:** Immediate derating of operating pressure from $145\text{ barg}$ to a maximum permissible working pressure of **$118\text{ barg}$** until permanent remedial actions are completed.
2. **Emergency Approval Note Requirement:** Maintenance & Inspection department to immediately draft a Formal Note for Approval (NFA) for either:
   - Automated GTAW weld overlay restoration ($5.0\text{ mm}$ 347 SS) during the upcoming October turnaround, OR
   - Emergency replacement of bottom head assembly.
3. **Radiographic Confirmation:** 100% profile radiography of nozzle attachment welds within 48 hours.

---

**Inspected & Reported By:**  
*Er. S. Chandrasekhar, ASNT Level-III (UT/RT/MPI)*  
Lead Inspection Engineer (Static Equipment & NDT)  

**Reviewed & Counter-signed By:**  
*B. N. Talukdar*  
Deputy General Manager (Quality Assurance & Inspection)  
Guwahati Refinery, Indian Oil Corporation Limited  
