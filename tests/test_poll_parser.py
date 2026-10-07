from bs4 import BeautifulSoup
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
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th")]
    assert "Empresa" in headers
    assert "Error medio" in headers
