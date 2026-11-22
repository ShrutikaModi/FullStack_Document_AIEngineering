"""Recorded answers for the demo.

Recorded from the real assistant by evals/record_demo.py, then corrected by hand on
2026-11-22: wrong Amazon margins fixed, two unsupported NVIDIA claims removed, markers
placed after the figure or sentence they support, passages reloaded in full. Every
answer passes app/demo/checks.py. Re-running the recorder replaces this file.
"""

RECORDED = [{'id': 'apple-net-sales',
  'company': 'Apple',
  'kind': 'Single figure',
  'question': "What was Apple's total net sales in fiscal 2024?",
  'steps': ['Searching AAPL FY2024 filings: total net sales'],
  'answer': "Apple's total net sales in fiscal 2024 were $391,035 million [1].",
  'sources': [{'label': 1,
               'chunkId': 'bc477816-3e24-4b5f-9e02-fb4f1c1ddff0',
               'company': 'Apple Inc.',
               'ticker': 'AAPL',
               'formType': '10-K',
               'fiscalYear': 2024,
               'filingDate': '2024-11-01',
               'page': 35,
               'section': 'Item 8. Financial Statements and Supplementary Data',
               'excerpt': '2024 | 2023 | 2022 |\n'
                          '| iPhone | $ | 201,183 | $ | 200,583 | $ | 205,489 |\n'
                          '| Mac | 29,984 | 29,357 | 40,177 |\n'
                          '| iPad | 26,694 | 28,300 | 29,292 |\n'
                          '| Wearables, Home and Accessories | 37,005 | 39,845 | 41,241 |\n'
                          '| Services (1) | 96,169 | 85,200 | 78,129 |\n'
                          '| Total net sales | $ | 391,035 | $ | 383,285 | $ | 394,328 |\n'
                          '\n'
                          '(1)Services net sales include amortization of the deferred value of '
                          'services bundled in the sales price of certain products.\n'
                          '\n'
                          'Total net sales include $7.7 billion of revenue recognized in 2024 that '
                          'was included in deferred revenue as of September 30, 2023, $8.2 billion '
                          'of revenue recognized in 2023 that was included in deferred revenue as '
                          'of September 24, 2022, and $7.5 billion of revenue recognized in 2022 '
                          'that was included in deferred revenue as of September 25, 2021.',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm'}]},
 {'id': 'amazon-aws-margin',
  'company': 'Amazon',
  'kind': 'Comparison',
  'question': 'For Amazon, compare AWS operating income and margin against North America and '
              'International.',
  'steps': ['Searching AMZN FY2025 filings: Amazon Web Services operating income margin',
            'Searching AMZN FY2025 filings: North America operating income margin',
            'Searching AMZN FY2025 filings: International operating income margin'],
  'answer': 'In fiscal 2025, AWS had operating income of $45,606 million [1] on net sales of '
            '$128,725 million [2], an operating margin of about 35.43% (calculated from these '
            'figures). North America had operating income of $29,619 million [1] on net sales of '
            '$426,305 million [2], a margin of about 6.95%. International had operating income of '
            '$4,750 million [1] on net sales of $161,894 million [2], a margin of about 2.93%. AWS '
            'therefore had by far the highest margin of the three segments, followed by North '
            'America and then International.',
  'sources': [{'label': 1,
               'chunkId': 'b358b55f-86b2-4d1d-b622-3bdc5572b30c',
               'company': 'Amazon.com, Inc.',
               'ticker': 'AMZN',
               'formType': '10-K',
               'fiscalYear': 2025,
               'filingDate': '2026-02-06',
               'page': 27,
               'section': "Item 7. Management's Discussion and Analysis of Financial Condition and "
                          'Results of Operations',
               'excerpt': 'Table of Contents\n'
                          '\n'
                          'General and Administrative\n'
                          '\n'
                          'General and administrative costs in 2025 did not significantly change '
                          'compared to the prior year.\n'
                          '\n'
                          'Other Operating Expense (Income), Net\n'
                          '\n'
                          'Other operating expense (income), net was $763 million and $4.6 billion '
                          'during 2024 and 2025. The increase in 2025 was primarily related to the '
                          'settlement of a lawsuit with the Federal Trade Commission (the "FTC") '
                          'in Q3 2025, and also included the resolution of tax disputes associated '
                          'with our stores business in Italy, and physical stores and other asset '
                          'impairments.\n'
                          '\n'
                          'Operating Income\n'
                          '\n'
                          'Operating income by segment is as follows (in millions):\n'
                          '\n'
                          '| Year Ended December 31, |\n'
                          '| 2024 | 2025 |\n'
                          '| Operating Income |\n'
                          '| North America | $ | 24,967 | $ | 29,619 |\n'
                          '| International | 3,792 | 4,750 |\n'
                          '| AWS | 39,834 | 45,606 |\n'
                          '| Consolidated | $ | 68,593 | $ | 79,975 |\n'
                          '\n'
                          'Operating income was $68.6 billion and $80.0 billion for 2024 and 2025. '
                          'Operating income for 2025 includes charges of $2.5 billion we recorded '
                          'in Q3 2025 related to the settlement of a lawsuit with the FTC and $2.7 '
                          'billion, of which $1.8 billion was recorded in Q3 2025, of estimated '
                          'severance costs primarily related to planned role eliminations. We '
                          'believe that operating income is a more meaningful measure than gross '
                          'profit and gross margin due to the diversity of our product categories '
                          'and services. For more information on the operating expenses that '
                          'impact segment operating income, see "Operating Expenses" and the '
                          'descriptions of operating expense line item changes on pages 25 to 27, '
                          'and "Note 10 - Segment Information" on page 67.\n'
                          '\n'
                          'The increase in North America operating income in 2025, compared to the '
                          'prior year, is primarily due to increased unit sales and increased '
                          'advertising sales, partially offset by increased fulfillment, '
                          'technology and infrastructure, shipping, and other operating costs. '
                          'Changes in foreign exchange rates negatively impacted operating income '
                          'by $204 million in 2025.\n'
                          '\n'
                          'The increase in International operating income in 2025, compared to the '
                          'prior year, is primarily due to increased unit sales and increased '
                          'advertising sales, partially offset by increased fulfillment and '
                          'shipping costs. Changes in foreign exchange rates positively impacted '
                          'operating income by $903 million in 2025.\n'
                          '\n'
                          'The increase in AWS operating income in 2025, compared to the prior '
                          'year, is primarily due to increased sales, partially offset by spending '
                          'on technology infrastructure that was primarily driven by additional '
                          'investments to support AWS business growth. Changes in foreign exchange '
                          'rates negatively impacted operating income by $341 million in 2025.\n'
                          '\n'
                          'Interest Income and Expense',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm'},
              {'label': 2,
               'chunkId': 'abc33011-9edd-4d8a-b1c7-8531ff558873',
               'company': 'Amazon.com, Inc.',
               'ticker': 'AMZN',
               'formType': '10-K',
               'fiscalYear': 2025,
               'filingDate': '2026-02-06',
               'page': 68,
               'section': 'Item 8. Financial Statements and Supplementary Data',
               'excerpt': 'Table of Contents\n'
                          '\n'
                          'North America\n'
                          '\n'
                          'The North America segment primarily consists of amounts earned from '
                          'retail sales of consumer products (including from sellers) and '
                          'advertising and subscription services through North America-focused '
                          'online and physical stores. This segment includes export sales from '
                          'these online stores.\n'
                          '\n'
                          'International\n'
                          '\n'
                          'The International segment primarily consists of amounts earned from '
                          'retail sales of consumer products (including from sellers) and '
                          'advertising and subscription services through internationally-focused '
                          'online stores. This segment includes export sales from these '
                          'internationally-focused online stores (including export sales from '
                          'these online stores to customers in the U.S., Mexico, and Canada), but '
                          'excludes export sales from our North America-focused online stores.\n'
                          '\n'
                          'AWS\n'
                          '\n'
                          'The AWS segment consists of amounts earned from global sales of '
                          'compute, storage, database, and other services for start-ups, '
                          'enterprises, government agencies, and academic institutions.\n'
                          '\n'
                          'Information on reportable segments and reconciliation to consolidated '
                          'net income is as follows (in millions):\n'
                          '\n'
                          '| Year Ended December 31, |\n'
                          '| 2023 | 2024 | 2025 |\n'
                          '| North America |\n'
                          '| Net sales | $ | 352,828 | $ | 387,497 | $ | 426,305 |\n'
                          '| Operating expenses | 337,951 | 362,530 | 396,686 |\n'
                          '| Operating income | $ | 14,877 | $ | 24,967 | $ | 29,619 |\n'
                          '| International |\n'
                          '| Net sales | $ | 131,200 | $ | 142,906 | $ | 161,894 |\n'
                          '| Operating expenses | 133,856 | 139,114 | 157,144 |\n'
                          '| Operating income (loss) | $ | (2,656) | $ | 3,792 | $ | 4,750 |\n'
                          '| AWS |\n'
                          '| Net sales | $ | 90,757 | $ | 107,556 | $ | 128,725 |\n'
                          '| Operating expenses | 66,126 | 67,722 | 83,119 |\n'
                          '| Operating income | $ | 24,631 | $ | 39,834 | $ | 45,606 |\n'
                          '| Consolidated |\n'
                          '| Net sales | $ | 574,785 | $ | 637,959 | $ | 716,924 |\n'
                          '| Operating expenses | 537,933 | 569,366 | 636,949 |\n'
                          '| Operating income | 36,852 | 68,593 | 79,975 |\n'
                          '| Total non-operating income | 705 | 21 | 17,336 |\n'
                          '| Provision for income taxes | (7,120) | (9,265) | (19,087) |\n'
                          '| Equity-method investment activity, net of tax | (12) | (101) | (554) '
                          '|\n'
                          '| Net income | $ | 30,425 | $ | 59,248 | $ | 77,670 |',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm'}]},
 {'id': 'nvidia-data-center',
  'company': 'NVIDIA',
  'kind': 'Narrative disclosure',
  'question': 'How did NVIDIA describe demand drivers, customer concentration, and supply '
              'constraints for its Data Center business?',
  'steps': ['Searching NVDA FY2025 filings: Data Center business demand drivers customer '
            'concentration supply constraints'],
  'answer': 'In its fiscal 2025 10-K, NVIDIA said that advancements in accelerated computing and '
            'generative AI models, along with growth in model complexity and scale, drove '
            'increased demand for its Data Center systems [1]. Demand for its Hopper architecture '
            'drove its significant growth for the year, and it began shipping production systems '
            'of the Blackwell architecture in the fourth quarter of fiscal 2025 [2].\n'
            '\n'
            'On customer concentration, sales to two direct customers each represented 10% or more '
            'of total revenue in fiscal 2025, at 12% and 11%, and were primarily attributable to '
            'the Compute & Networking segment [3].\n'
            '\n'
            'On supply, NVIDIA said that higher purchase volumes and the integration of new '
            'suppliers and contract manufacturers make it more complex to manage multiple '
            'suppliers across production planning, execution and logistics [1]. It has entered '
            'into prepaid manufacturing and capacity agreements, and it may incur inventory '
            'provisions or impairments if its supply or capacity commitments exceed demand [1]. US '
            'export licensing requirements also apply to shipments of Data Center products, '
            'including Blackwell systems, to China and certain other countries [4].',
  'sources': [{'label': 1,
               'chunkId': 'b9e0f2dd-fe99-408b-8586-04c7f2a2a5c9',
               'company': 'NVIDIA Corporation',
               'ticker': 'NVDA',
               'formType': '10-K',
               'fiscalYear': 2025,
               'filingDate': '2025-02-26',
               'page': 36,
               'section': "Item 7. Management's Discussion and Analysis of Financial Condition and "
                          'Results of Operations',
               'excerpt': 'services can be incorrect and create volatility in our revenue or '
                          'supply levels. We may not be able to generate significant revenue from '
                          'them. Advancements in accelerated computing and generative AI models, '
                          'along with the growth in model complexity and scale, have driven '
                          'increased demand for our Data Center systems.\n'
                          '\n'
                          'We continue to increase our supply and capacity purchases with existing '
                          'and new suppliers to support our demand projections and increasing '
                          'complexity of our data center products. With these additions, we have '
                          'also entered and may continue to enter into prepaid manufacturing and '
                          'capacity agreements to supply both current and future products. The '
                          'increased purchase volumes and integration of new suppliers and '
                          'contract manufacturers into our supply chain creates more complexity in '
                          'managing multiple suppliers with variations in production planning, '
                          'execution and logistics. Our expanding product portfolio and varying '
                          'component compatibility and quality may lead to increased inventory '
                          'levels. We have incurred and may in the future incur inventory '
                          'provisions or impairments if our inventory or supply or capacity '
                          'commitments exceed demand for our products or demand declines.\n'
                          '\n'
                          'Product Transitions and New Product Introductions\n'
                          '\n'
                          'Product transitions are complex and we often ship both new and prior '
                          'architecture products simultaneously as our channel partners prepare to '
                          'ship and support new products. We are generally in various stages of '
                          'transitioning the architectures of our Data Center, Gaming, '
                          'Professional Visualization, and Automotive products. The computing '
                          'industry is experiencing a broader and faster launch cadence of '
                          'accelerated computing platforms to meet a growing and diverse set of AI '
                          'opportunities. We have introduced a new product and architecture '
                          'cadence of our Data Center solutions where we seek to complete new '
                          'computing solutions each year and provide a greater variety of Data '
                          'Center offerings. The increased frequency of these transitions and the '
                          'larger number of products and product configurations may magnify the '
                          'challenges associated with managing our supply and demand which may '
                          'further create volatility in our revenue. The increased frequency and '
                          'complexity of newly introduced products could result in quality or '
                          'production issues that could increase inventory provisions, warranty, '
                          'or other costs or result in product delays. We incur significant '
                          'engineering development resources for new products, and changes to our '
                          'product roadmap may impact our ability to develop other products or '
                          'adequately manage our supply chain cost. Customers may delay purchasing '
                          'existing products as we increase the frequency of new products or may '
                          'not be able to adopt our new products as fast as forecasted, both '
                          'impacting the timing of our revenue and supply chain cost. While we '
                          'have managed prior product transitions and have sold multiple product '
                          'architectures at the same time, these transitions are difficult, may '
                          'impair our ability to predict demand and impact our supply mix, and may '
                          'cause us to incur additional costs.\n'
                          '\n'
                          'Global Trade',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm'},
              {'label': 2,
               'chunkId': '7e3a3643-11b0-4c70-9a37-41981c1b09f4',
               'company': 'NVIDIA Corporation',
               'ticker': 'NVDA',
               'formType': '10-K',
               'fiscalYear': 2025,
               'filingDate': '2025-02-26',
               'page': 36,
               'section': "Item 7. Management's Discussion and Analysis of Financial Condition and "
                          'Results of Operations',
               'excerpt': "Item 7. Management's Discussion and Analysis of Financial Condition and "
                          'Results of Operations\n'
                          '\n'
                          'The following discussion and analysis of our financial condition and '
                          'results of operations should be read in conjunction with "Item 1A. Risk '
                          'Factors," our Consolidated Financial Statements and related Notes '
                          'thereto, as well as other cautionary statements and risks described '
                          'elsewhere in this Annual Report on Form 10-K, before deciding to '
                          'purchase, hold, or sell shares of our common stock.\n'
                          '\n'
                          'Overview\n'
                          '\n'
                          'Our Company and Our Businesses\n'
                          '\n'
                          'NVIDIA pioneered accelerated computing to help solve the most '
                          'challenging computational problems. Since our original focus on PC '
                          'graphics, we have expanded to several other large and important '
                          'computationally intensive fields. Fueled by the sustained demand for '
                          'exceptional 3D graphics and the scale of the gaming market, NVIDIA has '
                          'leveraged its GPU architecture to create platforms for scientific '
                          'computing, AI, data science, AV, robotics, and digital twin '
                          'applications.\n'
                          '\n'
                          'Our two operating segments are "Compute & Networking" and "Graphics." '
                          'Refer to Note 16 of the Notes to the Consolidated Financial Statements '
                          'in Part IV, Item 15 of this Annual Report on Form 10-K for additional '
                          'information.\n'
                          '\n'
                          'Headquartered in Santa Clara, California, NVIDIA was incorporated in '
                          'California in April 1993 and reincorporated in Delaware in April 1998.\n'
                          '\n'
                          'Recent Developments, Future Objectives and Challenges\n'
                          '\n'
                          'Demand and Supply\n'
                          '\n'
                          'Revenue growth in fiscal year 2025 was driven by data center compute '
                          'and networking platforms for accelerated computing and AI solutions. '
                          'Demand for our Hopper architecture drove our significant growth for the '
                          'full year. We began shipping production systems of the Blackwell '
                          'architecture in the fourth quarter of fiscal year 2025.\n'
                          '\n'
                          'Demand estimates for our products, applications, and services can be '
                          'incorrect and create volatility in our revenue or supply levels. We may '
                          'not be able to generate significant revenue from them. Advancements in '
                          'accelerated computing and generative AI models, along with the growth '
                          'in model complexity and scale, have driven increased demand for our '
                          'Data Center systems.',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm'},
              {'label': 3,
               'chunkId': 'adfa4637-22fa-4974-8ea8-66ebd6e46892',
               'company': 'NVIDIA Corporation',
               'ticker': 'NVDA',
               'formType': '10-K',
               'fiscalYear': 2025,
               'filingDate': '2025-02-26',
               'page': 41,
               'section': "Item 7. Management's Discussion and Analysis of Financial Condition and "
                          'Results of Operations',
               'excerpt': 'Table of Contents\n'
                          '\n'
                          'Reportable Segments\n'
                          '\n'
                          'Revenue by Reportable Segments\n'
                          '\n'
                          '| Year Ended |\n'
                          '| Jan 26, 2025 | Jan 28, 2024 | $   Change | %   Change |\n'
                          '| ($ in millions) |\n'
                          '| Compute & Networking | $ | 116,193 | $ | 47,405 | $ | 68,788 | 145 | '
                          '% |\n'
                          '| Graphics | 14,304 | 13,517 | 787 | 6 | % |\n'
                          '| Total | $ | 130,497 | $ | 60,922 | $ | 69,575 | 114 | % |\n'
                          '\n'
                          'Operating Income by Reportable Segments\n'
                          '\n'
                          '| Year Ended |\n'
                          '| Jan 26, 2025 | Jan 28, 2024 | $   Change | %   Change |\n'
                          '| ($ in millions) |\n'
                          '| Compute & Networking | $ | 82,875 | $ | 32,016 | $ | 50,859 | 159 | % '
                          '|\n'
                          '| Graphics | 5,085 | 5,846 | (761) | (13) | % |\n'
                          '| All Other | (6,507) | (4,890) | (1,617) | 33 | % |\n'
                          '| Total | $ | 81,453 | $ | 32,972 | $ | 48,481 | 147 | % |\n'
                          '\n'
                          'Compute & Networking revenue - The year over year increase was due to '
                          'strong demand for our accelerated computing and AI solutions. Revenue '
                          'from Data Center computing grew 162% driven primarily by demand for our '
                          'Hopper computing platform used for large language models, '
                          'recommendation engines, and generative AI applications. Revenue from '
                          'Data Center networking grew 51% driven by Ethernet for AI revenue, '
                          'which includes Spectrum-X end-to-end ethernet platform.\n'
                          '\n'
                          'Graphics revenue - The year over year increase was driven by sales of '
                          'our GeForce RTX 40 Series GPUs.\n'
                          '\n'
                          'Reportable segment operating income - The year over year increase in '
                          'Compute & Networking segment operating income was driven by growth in '
                          'revenue. The year over year decrease in Graphics segment operating '
                          'income was driven by an increase of 44% in segment operating expenses, '
                          'partially offset by growth in revenue.\n'
                          '\n'
                          'All Other operating loss - The year over year increase was due to an '
                          'increase in stock-based compensation expense reflecting employee growth '
                          'and compensation increases.\n'
                          '\n'
                          'Concentration of Revenue\n'
                          '\n'
                          'We refer to customers who purchase products directly from NVIDIA as '
                          'direct customers, such as AIBs, distributors, ODMs, OEMs, and system '
                          'integrators. We have certain customers that may purchase products '
                          'directly from NVIDIA and may use either internal resources or '
                          'third-party system integrators to complete their build. We also have '
                          'indirect customers, who purchase products through our direct customers; '
                          'indirect customers include CSPs, consumer internet companies, '
                          'enterprises, and public sector entities.\n'
                          '\n'
                          'Direct Customers - Sales to direct customers which represented 10% or '
                          'more of total revenue, all of which were primarily attributable to the '
                          'Compute & Networking segment, are presented in the following table:\n'
                          '\n'
                          '| Year Ended |\n'
                          '| Jan 26, 2025 | Jan 28, 2024 |\n'
                          '| Direct Customer A | 12 | % | * |\n'
                          '| Direct Customer B | 11 | % | 13 | % |\n'
                          '| Direct Customer C | 11 | % | * |\n'
                          '\n'
                          '* Less than 10% of total revenue.\n'
                          '\n'
                          'No customer represented 10% or more of total revenue for fiscal year '
                          '2023.',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm'},
              {'label': 4,
               'chunkId': '201df78a-ee8b-4975-9799-db82da99cb90',
               'company': 'NVIDIA Corporation',
               'ticker': 'NVDA',
               'formType': '10-K',
               'fiscalYear': 2025,
               'filingDate': '2025-02-26',
               'page': 37,
               'section': "Item 7. Management's Discussion and Analysis of Financial Condition and "
                          'Results of Operations',
               'excerpt': 'Table of Contents\n'
                          '\n'
                          'In July 2023, the USG informed us of an additional licensing '
                          'requirement for a subset of A100 and H100 products destined to certain '
                          'customers and other regions, including some countries in the Middle '
                          'East.\n'
                          '\n'
                          'In October 2023, the USG announced new and updated licensing '
                          'requirements that became effective in our fourth quarter of fiscal year '
                          '2024 for exports to China and Country Groups D1, D4, and D5 (including '
                          'but not limited to Saudi Arabia, the United Arab Emirates, and Vietnam, '
                          'but excluding Israel) of our products exceeding certain performance '
                          'thresholds, including, but not limited to, the A100, A800, H100, H800, '
                          'L4, L40, L40S and RTX 4090. The licensing requirements also apply to '
                          'the export of products exceeding certain performance thresholds to a '
                          'party headquartered in, or with an ultimate parent headquartered in, '
                          'Country Group D5, including China. On October 23, 2023, the USG '
                          'informed us that the licensing requirements were effective immediately '
                          'for shipments of our A100, A800, H100, H800, and L40S products '
                          '(removing the grace period granted by the official rule). Blackwell '
                          'systems, such as GB200 NVL 72 and NVL 36 as well as B200 are also '
                          'subject to these requirements and therefore require a license for any '
                          'shipment to certain entities and to China and Country Groups D1, D4 and '
                          'D5, excluding Israel. To date, we have not received licenses to ship '
                          'these restricted products to China. Additionally, we understand that '
                          'partners and customers have also not received a license to ship these '
                          'restricted products.\n'
                          '\n'
                          'We expanded our Data Center product portfolio to offer new solutions, '
                          'including those for which the USG does not require a license or advance '
                          'notice before each shipment. We ramped new products designed '
                          'specifically for China that do not require an export control license. '
                          'Our Data Center revenue in China grew in fiscal year 2025. As a '
                          'percentage of total Data Center revenue, it remains well below levels '
                          'seen prior to the onset of export controls in October 2023. The market '
                          'in China for datacenter solutions remains competitive. We will continue '
                          'to comply with export controls while serving our customers. To the '
                          'extent that a customer requires products covered by the licensing '
                          'requirements, we may seek a license for the customer but have no '
                          'assurance that the USG will grant such a license, or that the USG will '
                          'act on the license application in a timely manner or at all.',
               'sourceUrl': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm'}]}]
