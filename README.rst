openspace_rvdata
================

|Binder|

Ship track plots for `OpenSpace <https://www.openspaceproject.com>`__
pulling data from https://www.rvdata.us.

|image|

Minimum Working Example
-----------------------

Here's a snippet to pull data for
`RR2402 <https://www.rvdata.us/search/cruise/RR2402>`__.

::

   import openspace_rvdata.r2r2df as r2r
   import openspace_rvdata.tracks as trk
   cruise_id = "RR2402"
   url = r2r.get_r2r_url(cruise_id)
   mdf = r2r.get_cruise_metadata(url)
   gdf = r2r.get_cruise_nav(cruise_id)
   trk.get_cruise_asset(mdf)
   trk.get_cruise_keyframes("tmp/"+cruise_id+"_1min.geoCSV")

This will generate two dataframes: ``mdf``, containing metadata, and
``gdf``, containing time-referenced coordinates. It will save the data
in geoCSV format to a local folder /tmp, along with the two OpenSpace
assets required to view the cruise data in OpenSpace: ``RR2402.asset``
(metadata) and ``RR2402_keyframes.asset`` (coordinates).

Once you have generated the assets, you can import them into OpenSpace
by dragging and dropping the assets. You can also move them into your
local OpenSpace asset directory and add them to your profile. Refer to
the `OpenSpace
documentation <https://docs.openspaceproject.com/latest/creating-data-assets/asset-creation/assets.html>`__
for more information about creation and import of assets.

Software Architecture
---------------------

The highlighted blocks are OpenSpace assets.

.. code:: mermaid

   flowchart TD
       n1["cruise_id, DOI or vessel name"] --> n2["get_r2r_url"]
       n2 -- url --> n3["get_cruise_metadata"]
       n3 -- mdf --> n4["get_cruise_asset"]
       n4 --> n5["cruise_id.asset"]
       n6["cruise_id, sampling rate"] --> n7["get_cruise_nav"]
       n7 --> n8["geoCSV"]
       n8 --> n9["geocsv2geojson"] & n10["cruise_id.geojson"] & n11("plotly.express") & n13["get_cruise_keyframes"]
       n9 --> n10
       n11 --> n12[".html"]
       n13 --> n14["cruise_id_keyframes.asset"]

       n1@{ shape: manual-input}
       n2@{ shape: process}
       n5@{ shape: document}
       n6@{ shape: manual-input}
       n8@{ shape: document}
       n9@{ shape:document}
       n10@{ shape: document}
       n12@{ shape: docs}
       n14@{ shape: document}
       click n1 "https://www.rvdata.us/search/cruise/RR2402"
      
      style n5 fill:#669,stroke:#333,stroke-width:4px 
      style n14 fill:#669,stroke:#333,stroke-width:4px

Acknowledgments
---------------

Many thanks to the members of the `OpenSpace
Slack <https://openspacesupport.slack.com>`__, particularly `Alex
Bock <https://github.com/alexanderbock>`__ (Linköping University),
`Micah Acinapura <https://github.com/micahnyc>`__ (American Museum of
Natural History) and `James Hedberg <https://github.com/hedbergj>`__
(CCNY Planetarium), who provided guidance and example code.

Disclaimers
^^^^^^^^^^^

Google Gemini was used to prototype the code in this repository. The
authors are not affiliated with OpenSpace or R2R.

Citations
---------

- A. Bock et al., "OpenSpace: A System for Astrographics," in IEEE
  Transactions on Visualization and Computer Graphics, vol. 26, no. 1,
  pp. 633-642, Jan. 2020, doi: 10.1109/TVCG.2019.2934259.
- Rolling Deck to Repository: Supporting the marine science community
  with data management services from academic research expeditions,
  Carbotte, S.M., O’Hara, S., Stocks, K., Clark, P., Stolp, L., Smith,
  S.R., Briggs, K., Hudak, R., Miller, E., Olson, C.J., Shane, N.,
  Uribe, R., Arko, R., Chandler, C.L., Ferrini, V., Miller, S.P., Doyle,
  A., Holik, J. Frontiers in Marine Science, 9, p.1012756. 2022
- Plotly Technologies Inc. Collaborative data science. Montréal, QC,
  2015. https://plot.ly.

.. |image| image:: https://github.com/user-attachments/assets/c397de8c-c8c4-4e8a-8ade-32f351be42fb
.. |Binder| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/KCollins/openspace_rvdata/be5382802575c6826712fcce0f69245f550a21a1?urlpath=lab%2Ftree%2Fnotebooks%2FMWE.ipynb
   :alt: Launch Binder
