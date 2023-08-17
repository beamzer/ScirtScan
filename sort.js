function sortGrades(column) {
    let table = document.getElementById("myTable");
    let rows = table.rows;

    let sorted = Array.from(rows).slice(1).sort((a, b) => {
        let aValue = gradeToNumber(a.cells[column].innerText.trim());
        let bValue = gradeToNumber(b.cells[column].innerText.trim());

        return aValue - bValue;
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

function gradeToNumber(grade) {
    switch (grade) {
        case 'A++': return 10;
        case 'A+':  return 9;
        case 'A':   return 8;
        case 'A-':  return 7;
        case 'A--': return 6;
        case 'B':   return 5;
        case 'C':   return 4;
        case 'D':   return 3;
        case 'E':   return 2;
        case 'F':   return 1;
        default:    return 0; // for any unhandled grades or values
    }
}

function sortTable(column) {
   let table = document.getElementById("myTable");
   let rows = table.rows;

let sorted = Array.from(rows).slice(1).sort((a, b) => {
    let aValue = getSortValue(a.cells[column].innerText);
    let bValue = getSortValue(b.cells[column].innerText);

    return aValue - bValue;
});

function getSortValue(text) {
    if (text === "\u2716") { // &#10006; (✖)
        return -1;
    } else if (text === "\u003F") { // &quest; (?)
        return 0;
    } else if (text === "\u2705") { // &#x2705; (✅)
        return 1;
    } else {
        return parseFloat(text);
    }
}

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