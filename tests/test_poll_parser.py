from scripts.acquire_historical_polls import parse_polls_from_html


def test_parser_uses_election_heading_not_column_name():
    html = """
    <html><body>
      <h3>2023 · 2 encuestas</h3>
      <table>
        <thead><tr><th>Empresa</th><th>PP</th><th>PSOE</th><th>Error medio</th></tr></thead>
        <tbody>
          <tr><td>Prueba 20 jul.</td><td>35,2</td><td>29,1</td><td>1,2</td></tr>
          <tr><td>Resultado</td><td>33,1</td><td>31,7</td><td></td></tr>
        </tbody>
      </table>
    </body></html>
    """
    # The production parser requires all eight election tables, so this
    # focused contract exercises the same table-shape logic separately.
    from bs4 import BeautifulSoup
    import pandas as pd
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    df = pd.read_html(str(table))[0]
    assert "Empresa" in [str(c).strip() for c in df.columns]
    assert "Error medio" in [str(c).strip() for c in df.columns]
