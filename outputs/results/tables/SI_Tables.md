# Supplementary Information tables (LaTeX)

Written by `analysis/Analysis.ipynb`, which also writes Tables S2 to S4 on their own to `SI_Tables_S2_S4.tex`.
Each block is a `longtable` that needs `\usepackage{array,longtable}`. The captions use the
macros in `outputs/results/Manuscript_Parameters.tex`, so that file must be `\input` first.
`\cite{ref45}` and `\cite{ref46}` stand for references [45] and [46] (the Census Place and
ACS population sources); replace them with the project's citation keys.

## Table S1

```latex
\begin{longtable}{| >{\raggedright\arraybackslash}p{3.2cm} | >{\centering\arraybackslash}p{1.6cm} | >{\raggedright\arraybackslash}p{2.2cm} | >{\raggedleft\arraybackslash}p{1.2cm} | >{\raggedleft\arraybackslash}p{1.9cm} | >{\raggedright\arraybackslash}p{3.4cm} |}
\caption{Breakdown of 2024 Water Board manure and wastewater transport manifests by form template used. In total, there were \NManifestTemplates{} unique templates on \NManifestLayouts{} unique page formats. The percentages include the \NManifestsAnalyzed{} manifests analyzed in the main manuscript plus \NDuplicatesCag{} duplicates where a facility submitted two different form templates for the same hauling event(s).} \\
\hline
\textbf{Template ID} & \textbf{Attachment Letter} & \textbf{General Order Referenced} & \textbf{Page Count} & \textbf{Percent of All Submitted Manifests} & \textbf{File example} \\
\hline
R5-2007-0035 Software & D & R5-2007-0035 & 2 & 33.6\% & 13701 S Hwy 59 El Nido 2024 Dairy AR \\
\hline
R5-2007-0035 General Order & D & R5-2007-0035 & 2 & 42.4\% & 20000 Cedar Ave Tracy 2024 Dairy AR (manifests 1--2) \\
\hline
R5-2007-0035 Variant 1 & D & R5-2007-0035 & 2 & 0.5\% & 13775 Murphy Rd Escalon 2024 Dairy AR \\
\hline
R5-2007-0035 Variant 2 & D & R5-2007-0035 & 2 & 5.5\% & 348 E Monte Vista Rd Ceres 2024 Dairy AR \\
\hline
R5-2007-0035 Variant 3 & N/A & R5-2007-0035 & 2 & 0.1\% & 17399 E Avena Rd Escalon 2024 Dairy AR \\
\hline
R5-2007-0035 Variant 4 & D & R5-2007-0035 & 1 & 2.6\% & 2023AR\_F \& L Barcellos \#2\_7585 Avenue 152\_W Tulare \\
\hline
R5-2007-0035 Variant 5 & D & R5-2007-0035 & 1 & 2.1\% & 2024AR\_Faial Farms 2 Dairy \\
\hline
R5-2010-XXXX Attachment G & G & R5-2010-XXXX & 2 & 0.2\% & 2024AR\_The Dairy Inc\_6240 21st Ave\_Kings \\
\hline
R5-2010-XXXX Attachment F & F & R5-2010-XXXX & 2 & 0.1\% & 2024AR\_K A Vanderham Dairy\_12565 Ave 152\_Tulare \\
\hline
R5-2013-0122 General Order & D & R5-2013-0122 & 2 & 10.3\% & 13436 N Thornton Rd Lodi 2024 Dairy AR \\
\hline
R5-2017-0058 Variant 1 & D & R5-2017-0058 & 3 & 0.1\% & 2024AR\_Contente \& Co Ranch\_5730 20th Ave\_Kings \\
\hline
R5-2017-0000 &  & R5-2017-0000 & 2 & 0.6\% & 2024AR\_Cream Top Dairy\_13075 Ave 200\_Tulare \\
\hline
Provost Pritchard & N/A & N/A & 2 & 0.4\% & 2024AR\_Diamond D LLC Dairy\_9423 Idaho Ave\_Kings \\
\hline
UCANR & N/A & N/A & 1 & 0.1\% & 20000 Cedar Ave Tracy 2024 Dairy AR (manifest 3) \\
\hline
Unknown Variant 1 & N/A & N/A & 1 & 0.2\% & 2024AR\_Moonstone Dairy\_1305 Iona Avenue\_Kings \\
\hline
CAG018001 & 4 & CAG018001 & 1 & 1.2\% & 2024AR\_John Jongsma Dairy\_15434 Ave 192\_Tulare \\
\hline
Innovative Ag & N/A &  & 2 & 0.1\% & 2024AR\_South Creek Dairy\_11450 Avenue 64\_W Tulare \\
\hline
\end{longtable}
```

## Table S2

```latex
\begin{longtable}{| >{\raggedright\arraybackslash}p{4.4cm} | >{\raggedright\arraybackslash}p{1.6cm} | >{\raggedright\arraybackslash}p{1.9cm} | >{\raggedright\arraybackslash}p{5.2cm} |}
\caption{All manifest parameter fields and post-processing applied.} \\
\hline
\textbf{Parameter Name} & \textbf{Data Type} & \textbf{Manifest Type} & \textbf{Post-Processing Applied} \\
\hline
Origin Dairy Name & text & both &  \\
\hline
Origin Dairy Address & text & both & Filled from annual report address if missing. Geocoding \\
\hline
Hauler Name & text & both &  \\
\hline
Hauler Address & text & both & Geocoding \\
\hline
Destination Name & text & both &  \\
\hline
Destination Contact Address & text & both & Geocoding \\
\hline
Destination Address & text & both & Geocoding, querying the address together with its cross street and county first, if given \\
\hline
Destination Nearest Cross Street & text & both & Geocoding, only where two distinct street names are given and the geocoder returns a street intersection \\
\hline
Destination Type & text & both & Standardization of categories \\
\hline
Destination Assessor Parcel Number & text & both & Geocoding against the statewide parcel locator, within counties covered by ZIP codes in the manifest \\
\hline
Destination Latitude & numeric & both &  \\
\hline
Destination Longitude & numeric & both &  \\
\hline
Haul Date & text & both & Parsed into First Haul Date (if applicable) and Last Haul Date \\
\hline
Is Pipeline & boolean & both & Set true if ``pipeline'' or ``ditch'' is included in the manifest text \\
\hline
Is Trucked & boolean & both & Always true for manure. For wastewater, ``True'' if number of hauls, trucks, or tanks are mentioned, ``False'' if Is Pipeline, otherwise ``Unsure'' \\
\hline
Total Process Wastewater Exports (Gallons) & numeric & wastewater &  \\
\hline
Total Manure Amount (tons) & numeric & manure &  \\
\hline
Total Manure Amount (cubic yards) & numeric & manure & Converted to tons by dividing by Manure Density (cubic yards per ton) \\
\hline
Manure Density & numeric & manure &  \\
\hline
Manure Solids (\%) & numeric & manure &  \\
\hline
Manure Moisture (\%) & numeric & manure & Converted to Solids \% \\
\hline
Method Used to Determine Volume of Manure & text & manure & Broken out into Manure Mass per Haul (tons), Manure Volume per Haul (cubic yards), and Manure Number of Hauls as relevant \\
\hline
Method Used to Determine Volume of Wastewater & text & wastewater & Broken out into Wastewater Volume per Haul (Gallons), Wastewater Number of Hauls, Wastewater Hours Pumped (Hours), and Wastewater Pumping Rate (GPM), as relevant \\
\hline
\end{longtable}
```

## Table S3

```latex
\begin{longtable}{| >{\raggedright\arraybackslash}p{2.6cm} | >{\raggedright\arraybackslash}p{3.8cm} | >{\raggedright\arraybackslash}p{6.6cm} |}
\caption{Determining trucked versus pipeline wastewater transport.} \\
\hline
\textbf{Transport Type} & \textbf{Detection Keywords} & \textbf{Text Examples} \\
\hline
Pipeline & ``pipeline'' or ``ditch'' & (via concrete ditch)\newline Pipeline\newline LUMAR PIPELINE \\
\hline
Trucked & ``load'', ``haul'', or ``tank'' (without ``apply'' or ``applied'') & 247 Loads @ 9500 Gallons Per Load.\newline Haulers Calc\newline Hauler's Calculations\newline 100 Loads With Slurry Tankers-8400 Gallons/Load\newline Number Of Loads Multiplied By Tank Volume \\
\hline
\end{longtable}
```

## Table S4

```latex
\begin{longtable}{| >{\raggedright\arraybackslash}p{2.6cm} | >{\raggedright\arraybackslash}p{3.8cm} | >{\raggedright\arraybackslash}p{6.6cm} |}
\caption{Methods used to calculate wastewater volume.} \\
\hline
\textbf{Calculation Method} & \textbf{Data Extracted} & \textbf{Text Examples} \\
\hline
Flowrate-based & Hours pumped, pumping rate (GPM) & Gpm X Runtime\newline Run-Times Multiplied By The Gpm Of The Lagoon Pump.\newline 6 Hours @ 1000 Gpm\newline 20 Hours At 1500 Gallons Per Minute\newline Hours Pumped X 1200 Gpm\newline 8 Hours Of Liquid Manure @ 1000 Gallons Per Minute \\
\hline
Pond level-based & Pond level drop & Pond Drop Calculation Based On 5 Feet Drop In First Quarter\newline Pond Drop Calculations\newline PD \\
\hline
Haul-based & Number of hauls, volume per haul & 247 Loads @ 9500 Gallons Per Load.\newline 370 Loads X 10000 Gallons\newline Number Of Loads Multiplied By Tank Volume\newline 100 Loads With Slurry Tankers-8400 Gallons/Load\newline Slurry Tankers - 250 loads at 8,400 gallons per load.\newline Haulers Load Count-17 Loads At 9500 Gallons Per Load.\newline 150 Loads At 9500 Gals/Load\newline 60 Loads Of Surry @ 9500 Gallons Per Load.\newline 10000 Gallons Per Load X 282 Loads\newline @ 10000 Gallons Per Load \\
\hline
Other/Unspecified & Varies & Tank Capacity Multiplied By The Number Of Tanks Applied\newline Precipitation Records\newline Estimated Annual Total To Independent Farming Field.\newline PO \\
\hline
\end{longtable}
```

## Table S5

```latex
\begin{longtable}{| >{\raggedright\arraybackslash}p{4.2cm} | >{\raggedleft\arraybackslash}p{0.8cm} | >{\raggedleft\arraybackslash}p{1.5cm} | >{\raggedleft\arraybackslash}p{2.0cm} | >{\raggedleft\arraybackslash}p{2.4cm} | >{\raggedleft\arraybackslash}p{1.2cm} |}
\caption{Routed manure manifests versus dropped manure manifests. Rank-biserial correlations and p-values are from two-sided Mann-Whitney tests of dropped groups against the routed group (Fig. S7).} \\
\hline
\textbf{Group} & \textbf{$n$} & \textbf{Median} & \textbf{Median difference vs routed} & \textbf{Rank-biserial correlation} & \textbf{$p$} \\
\hline
\multicolumn{6}{|l|}{\textit{Manure per manifest record (tons)}} \\
\hline
Routed & 559 & 1,335.0 &  &  &  \\
\hline
No destination address & 12 & 1,825.9 & 490.9 & 0.19 & 0.261 \\
\hline
Outside Water Board & 4 & 2,575.0 & 1,240.0 & 0.17 & 0.568 \\
\hline
Failed geocode & 62 & 4,158.5 & 2,823.5 & 0.44 & $<$0.001 \\
\hline
Cross-county APN & 11 & 700.0 & $-$635.0 & $-$0.24 & 0.176 \\
\hline
Routing failed & 1 & 2,200.0 &  &  &  \\
\hline
Bad origin geocode & 14 & 3,181.0 & 1,846.0 & 0.48 & 0.002 \\
\hline
Bad destination geocode & 95 & 2,236.0 & 901.0 & 0.17 & 0.007 \\
\hline
Routing incorrect & 81 & 1,060.0 & $-$275.0 & $-$0.10 & 0.127 \\
\hline
All dropped & 280 & 1,990.0 & 655.0 & 0.15 & $<$0.001 \\
\hline
\multicolumn{6}{|l|}{\textit{Herd size of the origin dairy (animal units)}} \\
\hline
Routed & 480 & 2,587.9 &  &  &  \\
\hline
No destination address & 7 & 2,712.5 & 124.6 & 0.20 & 0.365 \\
\hline
Outside Water Board & 3 & 4,990.6 & 2,402.7 & 0.33 & 0.318 \\
\hline
Failed geocode & 48 & 5,125.2 & 2,537.3 & 0.30 & $<$0.001 \\
\hline
Cross-county APN & 11 & 1,999.6 & $-$588.3 & $-$0.25 & 0.156 \\
\hline
Routing failed & 1 & 122.4 &  &  &  \\
\hline
Bad origin geocode & 14 & 4,017.3 & 1,429.4 & 0.33 & 0.035 \\
\hline
Bad destination geocode & 81 & 1,882.6 & $-$705.4 & $-$0.17 & 0.017 \\
\hline
Routing incorrect & 68 & 2,184.1 & $-$403.8 & $-$0.15 & 0.049 \\
\hline
All dropped & 233 & 2,587.0 & $-$0.9 & $-$0.02 & 0.594 \\
\hline
\end{longtable}
```

## Table S6

```latex
\begin{longtable}{| >{\raggedleft\arraybackslash}p{0.8cm} | >{\raggedright\arraybackslash}p{3.8cm} | >{\raggedleft\arraybackslash}p{1.6cm} | >{\raggedleft\arraybackslash}p{1.3cm} | >{\raggedleft\arraybackslash}p{1.3cm} | >{\raggedleft\arraybackslash}p{1.3cm} | >{\raggedleft\arraybackslash}p{1.5cm} | >{\raggedright\arraybackslash}p{1.5cm} |}
\caption{Largest receivers of dairy-exported manure across \NManureRecords{} manure manifest records. The tonnage percentages are shares of total manifested manure exports from manifests with an address.} \\
\hline
\textbf{Rank} & \textbf{Destination} & \textbf{Tonnage} & \textbf{Records} & \textbf{Origin dairies} & \textbf{\% of tonnage} & \textbf{Cumulative \%} & \textbf{Address type} \\
\hline
1 & 2312 ALPINE MEADOWS CT WASCO & 168,913 & 13 & 3 & 7.17 & 7.17 & street \\
\hline
2 & P.O. Box 81498 BAKERSFIELD & 163,632 & 18 & 6 & 6.95 & 14.12 & P.O. Box \\
\hline
3 & 7559 AVE 152 TIPTON & 114,586 & 15 & 10 & 4.86 & 18.98 & street \\
\hline
4 & 13214 EBERLE RD BAKERSFIELD & 105,833 & 16 & 3 & 4.49 & 23.48 & street \\
\hline
5 & 6219 E PANAM LANE BAKERSFIELD & 90,560 & 11 & 1 & 3.84 & 27.32 & street \\
\hline
6 & 14982 ROAD 152 TIPTON & 70,133 & 9 & 6 & 2.98 & 30.30 & street \\
\hline
7 & P.O. Box 27 EDISON & 54,713 & 7 & 2 & 2.32 & 32.62 & P.O. Box \\
\hline
8 & 10909 GLEN CLOE PLACE LAMONT & 47,987 & 7 & 1 & 2.04 & 34.66 & street \\
\hline
9 & P.O. Box 20370 BAKERSFIELD & 47,247 & 7 & 2 & 2.01 & 36.66 & P.O. Box \\
\hline
10 & EL NIDO COYOTE RD & 37,044 & 5 & 2 & 1.57 & 38.24 & street \\
\hline
11 & 4322 SACO RD BAKERSFIELD & 36,100 & 6 & 2 & 1.53 & 39.77 & street \\
\hline
12 & 6801 AVENUE 120 PIXLEY & 32,050 & 4 & 1 & 1.36 & 41.13 & street \\
\hline
13 & SOUTH LAKE ROAD BAKERSFIELD & 27,638 & 3 & 1 & 1.17 & 42.30 & street \\
\hline
14 & 5175 SHAW AVE WINTON & 25,913 & 13 & 3 & 1.10 & 43.40 & street \\
\hline
15 & 19075 W THIRD AVE STEVINSON & 23,500 & 2 & 2 & 1.00 & 44.40 & street \\
\hline
16 & 9442 BEAR MTN BLVD & 21,225 & 2 & 2 & 0.90 & 45.30 & street \\
\hline
17 & 13076 AVE 368 VISALIA & 21,200 & 3 & 3 & 0.90 & 46.20 & street \\
\hline
18 & 7792 NICKLE RD DOS PALOS & 20,096 & 9 & 3 & 0.85 & 47.05 & street \\
\hline
19 & 19721 EXCELSIOR AVE RIVERDALE & 18,276 & 4 & 2 & 0.78 & 47.83 & street \\
\hline
20 & 23234 SECOND AVE STEVINSON & 17,820 & 5 & 3 & 0.76 & 48.59 & street \\
\hline
\end{longtable}
```

## Table S7

```latex
\begin{longtable}{| >{\raggedleft\arraybackslash}p{0.6cm} | >{\raggedleft\arraybackslash}p{0.8cm} | >{\raggedright\arraybackslash}p{1.4cm} | >{\raggedright\arraybackslash}p{1.8cm} | >{\raggedright\arraybackslash}p{1.2cm} | >{\raggedright\arraybackslash}p{2.0cm} | >{\raggedright\arraybackslash}p{1.3cm} | >{\raggedright\arraybackslash}p{1.2cm} | >{\raggedleft\arraybackslash}p{1.0cm} | >{\raggedleft\arraybackslash}p{0.9cm} | >{\raggedleft\arraybackslash}p{1.2cm} | >{\raggedleft\arraybackslash}p{1.2cm} |}
\caption{The ten longest validated manure trucking records sorted by one-way routed travel distance. Identical origin-destination pairs can have multiple trucking records, denoted here by the Route ID.} \\
\hline
\textbf{Rank} & \textbf{Route ID} & \textbf{Origin dairy} & \textbf{Origin address} & \textbf{Origin county} & \textbf{Destination address} & \textbf{Dest. type} & \textbf{Dest. county} & \textbf{One-way miles} & \textbf{Total trips} & \textbf{Manure (tons)} & \textbf{Loaded truck-mi} \\
\hline
1 & 387 & Dutch Door Dairy & 3493 Bvd Rd Merced Merced 95341 & Merced & 16510 Bacon Island Rd Stockton CA 95234 & Farmer & San Joaquin & 104.0 & 129 & 1,650.0 & 13,414 \\
\hline
2 & 104 & Troost Dairy & 27000 Road 9 Chowchilla Madera 93610 & Madera & 20177 S Macarthur Dr Tracy 95304 San Joaquin & Farmer & San Joaquin & 89.4 & 101 & 1,304.3 & 9,026 \\
\hline
3 & 105 & Troost Dairy & 27000 Road 9 Chowchilla Madera 93610 & Madera & 20177 S Macarthur Dr Tracy 95304 San Joaquin & Farmer & San Joaquin & 89.4 & 43 & 554.0 & 3,843 \\
\hline
4 & 107 & Troost Dairy & 27000 Road 9 Chowchilla Madera 93610 & Madera & 20177 S Macarthur Dr Tracy 95304 San Joaquin & Farmer & San Joaquin & 89.4 & 69 & 884.6 & 6,166 \\
\hline
5 & 249 & Flint Dairy & 6511 Flint Ave. Hanford Kings 93230 & Kings & 7745 E Sandymush Merced 95341 Merced & Farmer & Merced & 77.9 & 308 & 3,970.8 & 23,982 \\
\hline
6 & 474 & Van Tol Dairy No. 2 & 6756 County Road 30 Orland Glenn 95963 & Glenn & 82 West Liberty Road Gridle 95948 County & Composting Facility & Butte & 64.7 & 53 & 685.0 & 3,430 \\
\hline
7 & 70 & Morning Star Dairy Inc & 10262 W Elkhorn Ave Burrel Fresno 93607 & Fresno & 18919 Ave 23 Chowchilla 93610 Madera & Composting Facility & Madera & 50.6 & 153 & 1,968.2 & 7,741 \\
\hline
8 & 2 & Banos Dairy & 4667 Avenue 23 1/2 Chowchilla Madera 93610 & Madera & 1275 North Avenue Gustine 95322 North Avenue Merced & Broker & Merced & 47.5 & 140 & 1,800.0 & 6,650 \\
\hline
9 & 3 & Banos Dairy & 4667 Avenue 23 1/2 Chowchilla Madera 93610 & Madera & 1275 North Avenue Gustine 95322 North Avenue Merced & Broker & Merced & 47.5 & 164 & 2,100.0 & 7,790 \\
\hline
10 & 140 & Avalon Dairy & 27225 Rond Rd Wasco 93280 & Kern & 9442 Bear Mtn Blvd 93311 & Broker & Kern & 47.2 & 719 & 9,240.0 & 33,920 \\
\hline
\end{longtable}
```

## Table S8

```latex
\begin{longtable}{| >{\raggedleft\arraybackslash}p{1.2cm} | >{\raggedright\arraybackslash}p{6.0cm} | >{\raggedleft\arraybackslash}p{3.0cm} |}
\caption{Communities with the largest total manure trucking miles, based on borders provided by the Census Place dataset \cite{ref46}. Truck-miles are allotted based on the fraction of \RoadBufferM{} m road buffers falling inside the borders of each Census Place.} \\
\hline
\textbf{Rank} & \textbf{Place} & \textbf{Truck-miles} \\
\hline
1 & Tulare city & 49,299 \\
\hline
2 & Visalia city & 33,797 \\
\hline
3 & Shafter city & 26,521 \\
\hline
4 & Bakersfield city & 26,362 \\
\hline
5 & Lakeside CDP & 19,550 \\
\hline
6 & Turlock city & 19,371 \\
\hline
7 & Tipton CDP & 18,831 \\
\hline
8 & Hanford city & 16,642 \\
\hline
9 & Merced city & 15,779 \\
\hline
10 & Hilmar-Irwin CDP & 14,032 \\
\hline
11 & Modesto city & 13,117 \\
\hline
12 & Fresno city & 10,779 \\
\hline
13 & Pixley CDP & 9,933 \\
\hline
14 & Madera city & 9,168 \\
\hline
15 & Rosedale CDP & 7,831 \\
\hline
16 & McFarland city & 7,256 \\
\hline
17 & Atwater city & 6,730 \\
\hline
18 & Riverdale CDP & 6,691 \\
\hline
19 & Dos Palos Y CDP & 5,979 \\
\hline
20 & Walnut Grove CDP & 5,927 \\
\hline
\end{longtable}
```

## Table S9

```latex
\begin{longtable}{| >{\raggedleft\arraybackslash}p{1.2cm} | >{\raggedright\arraybackslash}p{6.0cm} | >{\raggedleft\arraybackslash}p{3.0cm} |}
\caption{Communities with the most manure trucking miles per resident. Population is derived from 2020-2024 ACS five-year estimates \cite{ref45}.} \\
\hline
\textbf{Rank} & \textbf{Place} & \textbf{Truck-miles per resident} \\
\hline
1 & Lakeside CDP & 24.23 \\
\hline
2 & Farmington CDP & 23.04 \\
\hline
3 & Dos Palos Y CDP & 21.90 \\
\hline
4 & Tuttle CDP & 21.75 \\
\hline
5 & Stevinson CDP & 21.23 \\
\hline
6 & El Nido CDP & 7.99 \\
\hline
7 & Raisin City CDP & 7.64 \\
\hline
8 & Tipton CDP & 6.61 \\
\hline
9 & Walnut Grove CDP & 6.40 \\
\hline
10 & Lanare CDP & 5.76 \\
\hline
11 & Fairmead CDP & 4.55 \\
\hline
12 & Volta CDP & 4.17 \\
\hline
13 & Peters CDP & 3.92 \\
\hline
14 & Bowles CDP & 3.71 \\
\hline
15 & Traver CDP & 2.93 \\
\hline
16 & Pixley CDP & 2.65 \\
\hline
17 & Hilmar-Irwin CDP & 2.29 \\
\hline
18 & Monmouth CDP & 2.23 \\
\hline
19 & Cherokee Strip CDP & 2.21 \\
\hline
20 & Artois CDP & 2.17 \\
\hline
\end{longtable}
```

## Table S10

```latex
\begin{longtable}{| >{\raggedleft\arraybackslash}p{1.2cm} | >{\raggedright\arraybackslash}p{6.0cm} | >{\raggedleft\arraybackslash}p{3.0cm} |}
\caption{Communities with the most manure trucking miles per square mile. Area of communities is derived from Census Place outlines \cite{ref46}.} \\
\hline
\textbf{Rank} & \textbf{Place} & \textbf{Truck-miles per mi$^2$} \\
\hline
1 & Tipton CDP & 10,908 \\
\hline
2 & Lakeside CDP & 10,833 \\
\hline
3 & Dos Palos Y CDP & 3,819 \\
\hline
4 & Hilmar-Irwin CDP & 3,573 \\
\hline
5 & East Tulare Villa CDP & 3,112 \\
\hline
6 & Cherokee Strip CDP & 2,876 \\
\hline
7 & Stevinson CDP & 2,705 \\
\hline
8 & Tulare city & 2,377 \\
\hline
9 & Bear Creek CDP & 2,337 \\
\hline
10 & Empire CDP & 2,281 \\
\hline
11 & Patterson Tract CDP & 2,223 \\
\hline
12 & Franklin CDP & 2,022 \\
\hline
13 & Gustine city & 1,934 \\
\hline
14 & Pixley CDP & 1,892 \\
\hline
15 & Escalon city & 1,876 \\
\hline
16 & Raisin City CDP & 1,710 \\
\hline
17 & Riverdale CDP & 1,705 \\
\hline
18 & Traver CDP & 1,670 \\
\hline
19 & Lanare CDP & 1,381 \\
\hline
20 & Monterey Park Tract CDP & 1,366 \\
\hline
\end{longtable}
```
