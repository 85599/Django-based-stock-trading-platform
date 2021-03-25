from bs4 import BeautifulSoup as bs
import os, glob
import re, contextlib
import urllib
import pandas as pd
from institutionList import institutions
import time, datetime
from dateutil.relativedelta import relativedelta


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 6 times faster than parse13F1.py, many times faster that parese13F.py

def parse_form_13F():
    '''updates the 13F data table'''
    #-----------re compilers-------------------------------------------
    t1 = time.time()
    rawstring = re.compile(r'<[\s\S]*?>') # general tag remover
    rawstringfilingref = re.compile(r'<[\s\S]*?>|\s') # general tag remover
    rawstringsecName = re.compile(r'<[\s\S]*?>|\*|/|\\|\'|,|"|\?|!') # format securties name from  13F-HR
    rawFindAhref = re.compile(r'href="[\s\S]*?>') # find href links
    rawSubAhref = re.compile(r'href="|">|\s') # remove a href tags
    rawFindFilingDate = re.compile(r'Filing Date</div>\n<div class="info">[\s\S]*?</div>')
    rawSubFilingDate = re.compile(r'Filing Date</div>\n<div class="info">|</div>')

    #get list of ciks/institution names from the master institutions.csv--------------------------------------

    # create 13F-HR table
    df13FdataFname = "csv\\StockOwnership\\13F\\*.csv"
    df13FdataFnamePath = os.path.join(BASE_DIR, df13FdataFname)

    columns = ['cusip', 'stock', 'cik', 'institution']
    monthlist = monthList()
    columns.extend(monthlist)
    myFiles = glob.glob(df13FdataFnamePath)
    # look for filing information
    # iterate through the CIK number and look for 13F-HR filing info from SEC max 10 filings
    # parse the resulting page and  extract links to individual filing page. This is not-
    # the link to `3F form ` itself. Just a pointer to the filing page
    # make the list
    # multiplier = 1
    for ind, fpath in enumerate(myFiles[2471:]):
        cik = re.sub(r'13F\\|\.', '', re.findall(r'13F[\s\S]*?\.', fpath)[0]).strip()
        outFname = "csv\\StockOwnership\\13F\\"+str(cik)+".csv"
        outFnamePath = os.path.join(BASE_DIR, outFname)
        dfOld = pd.read_csv(fpath, encoding = "ISO-8859-1")
        cusipList = dfOld['cusip'].tolist()
        listOfdataList = dfOld.values.tolist()
        linkList = []
        priorTo = time.strftime('%Y%m%d')

        urlCheckIf13F = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK="+str(cik)\
                        +"&type=13F-HR&output=xml&dateb="+priorTo+"&owner=exclude&count=1"
        urlCheckIf13F = re.sub(r'\s', '', urlCheckIf13F)
        print(urlCheckIf13F)
        with urllib.request.urlopen(urlCheckIf13F) as f:
            soup = bs(f, 'lxml')
            if "filinghref" in str(soup):
                for i in soup.find('filinghref'):
                    i = re.sub(rawstring, '', str(i))
                    if i[-1] != "l":
                        i +="l"
                    linkList.append(i)
            else:
                name = "No filings exist"
        soup = None

        # iterate through each link in the link list
        # parse the page to extract links to actual form 13F-HR
        # also extract the filing dates to use as the column names
        for link in linkList:
            xmlLinkList = []
            link = re.sub(r'\s', '', link)
            print(link)

            with urllib.request.urlopen(link) as xmlf:
                soup1 = bs(xmlf, 'lxml')
            for i in soup1.findAll("tr", { "class" : "blueRow" }):
                if "INFORMATION TABLE" in str(i):
                    xmlLinkList.append("https://www.sec.gov"+re.sub(rawSubAhref, '', re.findall(rawFindAhref, str(i))[0]))
            filingDate = re.sub(rawSubFilingDate, '', re.findall(rawFindFilingDate, str(soup1))[0]).strip()[:7]
            print("Institution:",cik,". (", ind+1, "of", len(myFiles), ")")
            print(xmlLinkList)
            print (filingDate)
            if xmlLinkList == []: # if there are no xml links delete the institution from csv
                break
            filingDateMax = "2015-01"
            soup1 = None
            #iterate through xmllink list
            # parse each page and extract security name and no of shares held
            # if time.mktime(datetime.datetime.strptime(filingDate,"%Y-%m").timetuple())\
            #     >time.mktime(datetime.datetime.strptime(filingDateMax,"%Y-%m").timetuple()):
            for k in xmlLinkList:
                k = re.sub(r'\s', '', k)
                dataDict = {}
                tk1 = time.time()
                with urllib.request.urlopen(k) as xmls:
                    soup2 = bs(xmls, 'lxml')
                securitesNames = soup2.findAll('nameofissuer')
                noOfShareList = soup2.findAll('sshprnamt')
                cusips = soup2.findAll('cusip')
                for i, l in enumerate(securitesNames):
                    securitesName = re.sub(rawstringsecName, ' ', str(l)).strip().replace("&amp;", "and")
                    shares = re.sub(rawstring, '', str(noOfShareList[i]))
                    cusip = re.sub(rawstring, ' ', str(cusips[i])).strip()
                    dataDict[securitesName] = [cusip, shares]
                if dataDict == {}:
                    securitesNames = re.findall(r'<ns1:nameofissuer>[\s\S]*?</ns1:nameofissuer>', str(soup2))
                    noOfShareList = re.findall(r'<ns1:sshprnamt>[\s\S]*?</ns1:sshprnamt>', str(soup2))
                    cusips = re.findall(r'<ns1:cusip>[\s\S]*?</ns1:cusip>', str(soup2))
                    for i, l in enumerate(securitesNames):
                        securitesName = re.sub(rawstringsecName, ' ', str(l)).strip().replace("&amp;", "and")
                        shares = re.sub(rawstring, '', str(noOfShareList[i]))
                        cusip = re.sub(rawstring, ' ', str(cusips[i])).strip()
                        dataDict[securitesName] = [cusip, shares]
                if dataDict == {}:
                    securitesNames = re.findall(r'<n1:nameofissuer>[\s\S]*?</n1:nameofissuer>', str(soup2))
                    noOfShareList = re.findall(r'<n1:sshprnamt>[\s\S]*?</n1:sshprnamt>', str(soup2))
                    cusips = re.findall(r'<n1:cusip>[\s\S]*?</n1:cusip>', str(soup2))
                    for i, l in enumerate(securitesNames):
                        securitesName = re.sub(rawstringsecName, ' ', str(l)).strip().replace("&amp;", "and")
                        shares = re.sub(rawstring, '', str(noOfShareList[i]))
                        cusip = re.sub(rawstring, ' ', str(cusips[i])).strip()
                        dataDict[securitesName] = [cusip, shares]
                if dataDict == {}:
                    securitesNames = re.findall(r'<ns4:nameofissuer>[\s\S]*?</ns4:nameofissuer>', str(soup2))
                    noOfShareList = re.findall(r'<ns4:sshprnamt>[\s\S]*?</ns4:sshprnamt>', str(soup2))
                    cusips = re.findall(r'<ns4:cusip>[\s\S]*?</ns4:cusip>', str(soup2))
                    for i, l in enumerate(securitesNames):
                        securitesName = re.sub(rawstringsecName, ' ', str(l)).strip().replace("&amp;", "and")
                        shares = re.sub(rawstring, '', str(noOfShareList[i]))
                        cusip = re.sub(rawstring, ' ', str(cusips[i])).strip()
                        dataDict[securitesName] = [cusip, shares]
                securitesNames = noOfShareList = cusips= soup2 = None
                tk2 = time.time()
                if tk1-tk2 < 0.1:
                    time.sleep(0.1)
                lenDatadict = len(dataDict)
                # iterate through the extracted securities name list
                # insert the institution name , CIK, filing date as coulmn and shares held
                # make pandas DataFrame
                t1 = time.time()
                for indx, (secName, value) in enumerate(dataDict.items()):
                    if value[0].startswith("0"):
                        value[0] = value[0][1:]
                        if value[0].startswith("0"):
                            value[0] = value[0][1:]
                            if value[0].startswith("0"):
                                value[0] = value[0][1:]
                    if value[0] in cusipList:
                        targetList = [i for i in listOfdataList if value[0].upper() in i]
                        indexToInsert = listOfdataList.index(targetList[0])
                        for col in columns:
                            if col not in dfOld.columns:
                                print (col, "missing! Adding new column")
                                targetList[0].insert(4, 0)
                        targetList[0] = targetList[0][:len(columns)]
                        indexInTargetList = columns.index(filingDate)
                        sharesAlreadyOwn = float(targetList[0][indexInTargetList])
                        if sharesAlreadyOwn != float(value[1]):
                            targetList[0][indexInTargetList] = sharesAlreadyOwn + float(value[1])
                            listOfdataList[indexToInsert] =  targetList[0]
                            print (secName, "Table updated")
                        else:
                            listOfdataList[indexToInsert] =  targetList[0]
                            print (secName, "Table not updated")
                    else:
                        dataList = [value[0].upper(), secName, int(cik),listOfdataList[0][3]]+[0]*len(monthlist)
                        dataList[columns.index(filingDate)] = value[1]
                        listOfdataList.append(dataList)
                        t2 = time.time()
                        print(round(indx/lenDatadict * 100, 2), round(t2-t1, 2), end="\r")

        if xmlLinkList != []:
            holdingDf = pd.DataFrame(listOfdataList, columns=columns)
            # with atomic_overwrite(df13FdataFnamePath) as f:
            holdingDf.to_csv(outFnamePath, sep=',', index=False, encoding = "utf-8")
            holdingDf = dataDict = listOfdataList = None
            print (secName, "Done")

    t2 = time.time() -t1
    # df13Fdata.sort_values('cusip', inplace=True)
    # with atomic_overwrite(df13FdataFnamePath) as f:
    #     df13Fdata.to_csv(f, sep=',', index=False, encoding = "utf-8")
    print("Time elapsed:", t2)

def monthList():
    months = []
    today = datetime.date.today()
    current = today - relativedelta(months=33)
    while current <= today:
        months.append(current.strftime("%Y-%m"))
        current += relativedelta(months=1)
    return months[::-1]

@contextlib.contextmanager
def atomic_overwrite(filename):
    originalToTemp = filename + "v1"
    temp = filename + '~'
    with open(temp, "w") as f:
        yield f
    os.rename(filename, originalToTemp)
    os.rename(temp, filename) # this will only happen if no exception was raised
    os.remove(originalToTemp)


if __name__ == '__main__':
    try:
        parse_form_13F()
    except:
        print("An error occured, restarting in 60 seconds...")
        time.sleep(60)
        parse_form_13F()
