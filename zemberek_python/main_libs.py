import re, ssl
from collections import Counter
import snowballstemmer
from nltk import download
from nltk.corpus import stopwords
import jpype
import os

## KULLANIMI ##
###############
# 1) Örnek corpusun cümlelerini parcalara ayırır fonksiyonu ile parçalanır kelime-kelime haline getirilir
#    ve gereksiz kelimeler atılır
# 2) Parçalara ayrılmış olan haber cümlenin öğelerine ayrılır
# 3) Cümlenin öğelerine ayrılmış olan kelimelerin kökleri bulunur bir listeye konulur


def _find_libjvm():
    java_home = os.environ.get('JAVA_HOME', None)
    jre_home = os.environ.get('JRE_HOME', None)
    if java_home is not None:
        return _find_libjvm_in_java_home(java_home)
    elif jre_home is not None:
        return _find_libjvm_in_jre_home(jre_home)
    else:
        raise ValueError('Either set one of JAVA_HOME and JRE_HOME environment variables, or pass a path value to libjvmpath argument.')
    
def _find_libjvm_in_java_home(path):
    if os.name == 'nt': # windows
        path = os.path.join(path, 'jre', 'bin', 'server', 'jvm.dll')
    else:
        path = os.path.join(path, 'jre', 'lib', 'amd64', 'server', 'libjvm.so')
    if os.path.exists(path):
        return path
    else:
        raise IOError('Could not find libjvm in {}. Please make sure that you set JAVA_HOME environment variable correctly, or pass a value to libjvmpath argument'.format(path))
        
def _find_libjvm_in_jre_home(path):
    if os.name == 'nt': # windows
        path = os.path.join(path, 'bin', 'server', 'jvm.dll')
    else:
        path = os.path.join(path, 'lib', 'amd64', 'server', 'libjvm.so')
    if os.path.exists(path):
        return path
    else:
        raise IOError('Could not find libjvm in {}. Please make sure that you set JRE_HOME environment variable correctly, or pass a value to libjvmpath argument'.format(path))

class zemberek_api:
    def __init__(self,libjvmpath=None,zemberekJarpath=os.path.join(os.path.dirname(__file__), 'zemberek-tum-2.0.jar')):
        if libjvmpath is not None:
            self.libjvmpath = libjvmpath
        else:
            self.libjvmpath = _find_libjvm()
        self.zemberekJarpath = zemberekJarpath

    def zemberek(self):
        try:
            jpype.startJVM(self.libjvmpath, "-Djava.class.path=" + self.zemberekJarpath, "-ea")
            Tr = jpype.JClass("net.zemberek.tr.yapi.TurkiyeTurkcesi")
            tr = Tr()
            Zemberek = jpype.JClass("net.zemberek.erisim.Zemberek")
            zemberek_r = Zemberek(tr)
            return zemberek_r
        except:
            print("libjvm veya zemberek.jar dosyalarının pathleri yanlış yerde! ")



class ZemberekTool:
    def __init__(self,zemberek):
        self.zemberek_api = zemberek

    def separator(self, text):
        sperator_r = re.sub(r'[^\w\s]', ' ', text).lower()
        sperator_r = ' '.join(sperator_r.split())

        return sperator_r

    def frekans(self, list_x):
        counts = Counter(list_x)

        return counts

    def cumleyi_parcalara_ayir(self, corpus):
        ## cümlede gereksiz olan işaretlemeler ve boşluklar silindi
        ## haber içersinde kaç tane hangi kelimeden var
        body = self.separator(str(corpus))
        corpus_with_split = self.frekans(body.split())
        stopwords_list = stopwords.words('turkish')
        ## gereksiz bağlaçlar silindi
        filtered_words = [word for word in corpus_with_split if word not in stopwords_list]
        return filtered_words

    def ogelere_ayir(self, kelime):
        ## bu  kısım tekil kelime
        yanit = self.zemberek_api.kelimeCozumle(kelime)
        if len(yanit) < 1:
            return None

        try:
            x = str(yanit[0])  # java yanıtını str'e dönüştürdüm
            words = [x.replace('{', '')
                         .replace('}', '')
                         .replace("Icerik", '')
                         .replace("Kok", '')
                         .replace("Ekler", '')
                         .replace(":", '')
                         .replace("tip", ' ')
                         .replace("  ", ",")
                         .replace(" ", "")]
            words = ','.join(words)
            cumlenin_ogeleri = [value for value in words.split(',')]
            dict = ({"Icerik": cumlenin_ogeleri[0], "Kok": cumlenin_ogeleri[1], "tip": cumlenin_ogeleri[2],
                     "Ekler": cumlenin_ogeleri[3]})

            return dict
        except:
            pass

    def metinde_gecen_kokleri_bul(self, corpus):
        kelimeler = self.cumleyi_parcalara_ayir(corpus)
        metin_kokler_lst = []
        snow = snowballstemmer.stemmer('turkish')
        for i, item in enumerate(kelimeler):
            ## None degerlerin kok,içerik vs olmadıgı için NoneType hatası veriyor bu yüzden try-exp
            ## eger tip bulmak istersen tip;ekler bulmak istersen ekler yaz ogelere_ayir fonksiyonunun dict kısmına bakabilirsin
            try:
                sonuc = self.ogelere_ayir(kelimeler[i])["Kok"]
                metin_kokler_lst.append(sonuc)
            except:
                snow_result = snow.stemWord(kelimeler[i])
                metin_kokler_lst.append(snow_result)

        return metin_kokler_lst

    def kelime_onerici(self, kelime):
        yanit = self.zemberek_api.oner(kelime)
        yanit = str(yanit).replace('"', "").replace("(", "").replace(")", "").replace("'", "").split(",")

        return yanit

    def kelime_hecele(self, kelime):

        try:
            yanit = self.zemberek_api.hecele(kelime)
            ## str  ile java string tipini python str tipine dönüştürdüm
            ## listeye döndürmek için böyle bir yöntem yaptım şimdilik
            yanit = str(yanit).replace('"', "").replace("(", "").replace(")", "").replace("'", "").split(",")

            return yanit

        except:
            print(" '\033[1m'  << Kelime_hecele fonksiyonu >> Birden fazla kelime girdiniz")


class nltk_download:
    def __init__(self):
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context

        download()