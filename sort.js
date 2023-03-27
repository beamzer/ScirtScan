<script>
    function sortTable(column) {
        let table = document.getElementById("myTable");
        let rows = table.rows;
        let sorted = Array.from(rows).slice(1).sort((a, b) => {
            let aValue = a.cells[column].innerText;
            let bValue = b.cells[column].innerText;

            if (aValue < bValue) {
                return -1;
            } else if (aValue > bValue) {
                return 1;
            } else {
                return 0;
            }
        });

        let isSorted = true;
        for (let i = 1; i < rows.length - 1; i++) {
            if (rows[i].cells[column].innerText !== sorted[i - 1].cells[column].innerText) {
                isSorted = false;
                break;
            }
        }

        if (isSorted) {
            sorted.reverse();
        }

        for (let i = 1; i < rows.length; i++) {
            table.tBodies[0].appendChild(sorted[i - 1]);
        }
    }

</script>
