# Pattern annotation and CAD exchange (DXF-AAMA, DXF-ASTM) {#pattern-annotation-cad-exchange}

- **Aliases**: DXF-AAMA, DXF-ASTM, ASTM D6673, pattern file exchange, pattern markings; fr: echange de fichiers patron
- **Family**: cutting and production
- **Recognize**: .dxf pattern files with several layers (cut line, notches, grain line, drill holes, text)
  exchanged between CAD systems (Gerber, Lectra, Optitex, Clo, others).
- **Pieces**: every piece with name, size, number to cut, grain line, notches, drill holes and, if present,
  grade rules.
- **Shape**: not a shape. Pattern annotation (finishes.md): name, size, quantity, "on fold" when relevant,
  fabric direction when nap exists, grain line parallel to the selvedge (45 degrees for bias). ASTM D6673
  is a DXF-based practice (AutoCAD version 13 DXF); it specifies that the pattern file complies with DXF. A
  drill hole is a point that is part of a piece but not part of any line; drill holes may mark pocket or
  buttonhole placement. The grade rules are exchanged in a separate ASCII rule table file in the ASTM form
  (the AAMA files embed them as movement values). Layers in AAMA files, reported in secondary sources:
  1 cut outline, 2 turn or grade points, 4 notch, 8 draw/ink, 11 internal cut, 13 drill, 14 sew line,
  19 text, 26 reference. These layer numbers come from forum posts and a Scribd document and were
  not checked against the AAMA publication. D6673 revision 2010 was withdrawn in 2019 (a catalogue listing).
  Source: ASTM store/ANSI listings, Minerva blog, rhino forum, Scribd (as noted).
- **Drafting**: 1) Name every piece and set quantity. 2) Put cut lines, notches, drill holes and grain
  lines on the layers expected by the receiver. 3) Send a sample file to the receiver and ask for its
  own sample. 4) Test import of a simple piece before a full set.
- **Sewing order**: not applicable
- **Finishes and notions**: rule table file, a pattern list (name, size, cut count)
- **Fabrics**: not applicable
- **Fit faults**: scale error from unit mismatch: check a 10 cm test square (finishes.md).
- **Variants**: #notches-drill-holes, #seam-allowance-conventions
- **CLO3D**: import and export DXF (AAMA/ASTM) from the file menu; test with a small piece; check units and
  that seam allowances are not double-counted.
- **Confidence**: ASTM D6673 identity and drill-hole definition: verified (search); layer numbers:
  secondary, unverified; ask the receiving system for a sample file.
- **Status**: unverified
