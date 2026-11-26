(function () {
    function initDegreeCategoryFilter() {
        const categorySelect = document.getElementById('id_degree_category');
        const batchSelect = document.getElementById('id_issuance_batch');
        const degreeSelect = document.getElementById('id_degree');
        if (!degreeSelect || (!categorySelect && !batchSelect)) {
            return;
        }

        // Lưu toàn bộ option/optgroup gốc để lọc kết hợp Loại văn bằng + Đợt phát hành
        const originalNodes = Array.from(degreeSelect.children).map((node) => node.cloneNode(true));

        function matchesFilters(opt) {
            const selectedCategory = categorySelect ? categorySelect.value : '';
            const selectedBatch = batchSelect ? batchSelect.value : '';
            const okCategory = !selectedCategory || opt.dataset.degreeType === selectedCategory;
            const okBatch = !selectedBatch || opt.dataset.batch === selectedBatch;
            return okCategory && okBatch;
        }

        function filterDegrees() {
            const previousValue = degreeSelect.value;

            while (degreeSelect.firstChild) {
                degreeSelect.removeChild(degreeSelect.firstChild);
            }

            let hasPreviousStillValid = false;

            originalNodes.forEach((origNode) => {
                if (origNode.tagName === 'OPTION') {
                    if (!origNode.value) {
                        degreeSelect.appendChild(origNode.cloneNode(true));
                    } else if (matchesFilters(origNode)) {
                        degreeSelect.appendChild(origNode.cloneNode(true));
                        if (origNode.value === previousValue) {
                            hasPreviousStillValid = true;
                        }
                    }
                    return;
                }

                if (origNode.tagName === 'OPTGROUP') {
                    const matchingOptions = Array.from(origNode.children).filter(matchesFilters);
                    if (matchingOptions.length > 0) {
                        const groupClone = document.createElement('optgroup');
                        groupClone.label = origNode.label;
                        matchingOptions.forEach((opt) => {
                            groupClone.appendChild(opt.cloneNode(true));
                            if (opt.value === previousValue) {
                                hasPreviousStillValid = true;
                            }
                        });
                        degreeSelect.appendChild(groupClone);
                    }
                }
            });

            degreeSelect.value = hasPreviousStillValid ? previousValue : '';
        }

        // Đồng bộ sẵn bộ lọc nếu đang mở bản ghi đã chọn văn bằng
        const currentSelectedOption = degreeSelect.querySelector('option:checked');
        if (currentSelectedOption && currentSelectedOption.value) {
            if (categorySelect && !categorySelect.value && currentSelectedOption.dataset.degreeType) {
                categorySelect.value = currentSelectedOption.dataset.degreeType;
            }
            if (batchSelect && !batchSelect.value && currentSelectedOption.dataset.batch) {
                batchSelect.value = currentSelectedOption.dataset.batch;
            }
        }

        filterDegrees();
        if (categorySelect) {
            categorySelect.addEventListener('change', filterDegrees);
        }
        if (batchSelect) {
            batchSelect.addEventListener('change', filterDegrees);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDegreeCategoryFilter);
    } else {
        initDegreeCategoryFilter();
    }
})();
