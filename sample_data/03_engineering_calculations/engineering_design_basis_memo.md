# BHARAT PETROLEUM & REFINERIES CORPORATION LIMITED
## CENTRAL ENGINEERING DESIGN DIVISION (PROCESS & PIPING GROUP)
### TECHNICAL MEMORANDUM: ASME SECTION VIII DIV 1 WALL THICKNESS CALCULATION

**Document ID:** CED-M-CALC-2026-0412  
**Revision:** Rev-2 (Approved for Construction)  
**Subject:** Mechanical Design Calculation for High-Pressure Hydrocracker High-Pressure Separator Vessel (`11-V-102`)  
**Design Code:** ASME Boiler & Pressure Vessel Code (BPVC), Section VIII, Division 1 (2023 Edition) + API 510  

---

### 1. DESIGN BASIS & PROCESS PARAMETERS

| Parameter | Symbol | Value | Units | Notes / Basis |
| :--- | :--- | :--- | :--- | :--- |
| Internal Design Pressure | $P$ | 14.50 | $\text{MPa}$ (145.0 barg) | Operating pressure + 10% safety margin |
| Design Temperature | $T$ | 285 | $^\circ\text{C}$ | Severe hydrogen service operating window |
| Inside Diameter (Cylindrical Shell) | $D_i$ | 2400.0 | $\text{mm}$ | Process capacity requirement |
| Inside Radius | $R$ | 1200.0 | $\text{mm}$ | $R = D_i / 2$ |
| Shell Material Specification | - | SA-387 Gr 22 Cl 2 | - | $2.25\text{Cr}-1\text{Mo}$ Low Alloy Steel (Hydrogen Embrittlement Resistant) |
| Maximum Allowable Stress @ 285°C | $S$ | 138.0 | $\text{MPa}$ | ASME BPVC Section II, Part D, Table 1A |
| Joint Efficiency (Full Radiography) | $E$ | 1.00 | - | UW-11(a) Type 1 Butt Welds (100% RT + UT) |
| Corrosion Allowance (Internal Cladding) | $CA$ | 4.0 | $\text{mm}$ | 3.0 mm 347 SS weld overlay + 1.0 mm base metal margin |
| Head Geometry | - | 2:1 Semi-Ellipsoidal | - | Seamless forged knuckle/crown |

---

### 2. GOVERNING GOVERNING EQUATIONS (ASME SECTION VIII DIV 1)

#### 2.1 Cylindrical Shell Wall Thickness (Paragraph UG-27(c)(1))
Circumferential (Hoop) Stress governs the required thickness of cylindrical pressure vessel shells:
$$t_{\text{shell, req}} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P} + CA$$

Where:
- $P = 14.50\text{ MPa}$
- $R = 1200.0\text{ mm}$
- $S = 138.0\text{ MPa}$
- $E = 1.00$
- $CA = 4.0\text{ mm}$

**Step-by-Step Numerical Substitution:**
$$S \cdot E = 138.0 \cdot 1.00 = 138.0\text{ MPa}$$
$$0.6 \cdot P = 0.6 \cdot 14.50 = 8.70\text{ MPa}$$
$$\text{Denominator} = 138.0 - 8.70 = 129.30\text{ MPa}$$
$$\text{Numerator} = P \cdot R = 14.50 \cdot 1200.0 = 17400\text{ MPa}\cdot\text{mm}$$
$$t_{\text{pressure}} = \frac{17400}{129.30} = 134.57\text{ mm}$$
$$t_{\text{shell, req}} = 134.57 + 4.0 = \mathbf{138.57\text{ mm}}$$

*Selected Nominal Plate Thickness (Standard Mill Plate):* **$145.0\text{ mm}$** (provides $6.43\text{ mm}$ positive safety margin above code minimum).

---

#### 2.2 2:1 Semi-Ellipsoidal Formed Heads (Paragraph UG-32(d))
For standard 2:1 ellipsoidal heads where $K = 1.0$:
$$t_{\text{head, req}} = \frac{P \cdot D_i}{2 \cdot S \cdot E - 0.2 \cdot P} + CA$$

**Step-by-Step Numerical Substitution:**
$$2 \cdot S \cdot E = 2 \cdot 138.0 \cdot 1.00 = 276.0\text{ MPa}$$
$$0.2 \cdot P = 0.2 \cdot 14.50 = 2.90\text{ MPa}$$
$$\text{Denominator} = 276.0 - 2.90 = 273.10\text{ MPa}$$
$$\text{Numerator} = 14.50 \cdot 2400.0 = 34800\text{ MPa}\cdot\text{mm}$$
$$t_{\text{pressure, head}} = \frac{34800}{273.10} = 127.43\text{ mm}$$
$$t_{\text{head, req}} = 127.43 + 4.0 = \mathbf{131.43\text{ mm}}$$

*Selected Nominal Head Thickness:* **$140.0\text{ mm}$** (Formed from heavy forged dish).

---

### 3. MAXIMUM ALLOWABLE WORKING PRESSURE (MAWP) CHECK
In corroded condition ($t_{\text{nominal}} - CA = 145.0 - 4.0 = 141.0\text{ mm}$):
$$MAWP_{\text{shell}} = \frac{S \cdot E \cdot t}{R + 0.6 \cdot t} = \frac{138.0 \cdot 1.00 \cdot 141.0}{1200.0 + 0.6 \cdot 141.0} = \frac{19458}{1284.6} = \mathbf{15.15\text{ MPa (151.5 barg)}}$$

Since $MAWP (15.15\text{ MPa}) > P_{\text{design}} (14.50\text{ MPa})$, the shell thickness design is fully compliant with ASME Section VIII Div 1 rules.

---

### 4. HYDROSTATIC PROOF TEST PRESSURE (UG-99(b))
$$P_{\text{test}} = 1.3 \cdot MAWP \cdot \left(\frac{S_{\text{ambient}}}{S_{\text{design}}}\right)$$
For SA-387 Gr 22 Cl 2:
- $S_{\text{ambient}} (20^\circ\text{C}) = 148.0\text{ MPa}$
- $S_{\text{design}} (285^\circ\text{C}) = 138.0\text{ MPa}$
- Ratio $= 148.0 / 138.0 = 1.0725$

$$P_{\text{test}} = 1.3 \cdot 15.15 \cdot 1.0725 = \mathbf{21.12\text{ MPa (211.2 barg)}}$$
Duration: Hold at $211.2\text{ barg}$ for a minimum of 2.0 hours, followed by 100% magnetic particle examination (MPI) of all nozzle attachment welds.

---

**Calculated By:** Er. Anita Deshmukh, Lead Mechanical Vessel Engineer  
**Verified By:** Dr. K. S. Murthy, Chief Static Equipment Specialist  
**Code Stamp Inspection Authority:** Lloyds Register Industrial Services (India)  
