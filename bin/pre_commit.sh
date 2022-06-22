#!/bin/bash

BASE_PATH="$(dirname "$0")"

source "$BASE_PATH/colors.sh"

EXIT_CODE=0

echo "${Cyan}Formatting code with black...$Color_Off"
black -l 120 django_opensearch_dsl tests
echo ""

echo -n "${Cyan}Running pycodestyle... $Color_Off"
out=$(pycodestyle django_opensearch_dsl tests)
if [ "$?" -ne 0 ] ; then
  echo "${Red}Error !$Color_Off"
  echo -e "$out"
  EXIT_CODE=1
else
  echo "${Green}Ok ✅ $Color_Off"
fi
echo ""


echo -n "${Cyan}Running pydocstyle... $Color_Off"
out=$(pydocstyle --count django_opensearch_dsl tests)
if [ "${PIPESTATUS[0]}" -ne 0 ] ; then
  echo "${Red}Error !$Color_Off"
  echo -e "$out"
  EXIT_CODE=1
else
  echo "${Green}Ok ✅ $Color_Off"
fi
echo ""


if [ $EXIT_CODE = 1 ] ; then
   echo "${Red}⚠ You must fix the errors before committing ⚠$Color_Off"
   exit $EXIT_CODE
fi
echo "${Purple}✨ You can commit without any worry ✨$Color_Off"
